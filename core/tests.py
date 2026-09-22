"""
Tests de non-régression sur la remédiation « fuite d'informations techniques »
(audit de sécurité 2026).

Le principe à préserver est une séparation stricte entre deux canaux :

  • les messages MÉTIER (RAISERROR applicatif, numéro >= 50000) sont écrits en
    français pour l'utilisateur final et doivent lui parvenir intacts ;
  • tout le reste — erreurs système de SQL Server, bruit du driver ODBC,
    exceptions Python — ne doit JAMAIS atteindre le client : seulement les logs.

Ces tests ne touchent ni la base ni le réseau (DATABASES est vide, l'appel SQL
est simulé). Lancement :

    python manage.py test core
"""
from unittest.mock import patch

import pyodbc
from django.test import SimpleTestCase, RequestFactory

from core import db, views
from core.db import _extract_sql_message


# Préfixe exact que pyodbc place devant les messages remontés par SQL Server.
PREFIXE_ODBC = "[42000] [Microsoft][ODBC Driver 17 for SQL Server][SQL Server]"

# Marqueurs dont la présence dans une réponse HTTP signe une fuite technique.
MARQUEURS_TECHNIQUES = [
    'ODBC', 'Microsoft', 'SQL Server', 'SQLExecDirect', 'SQLMoreResults',
    'pyodbc', 'ft_EVER_', 'dbo.', 'Traceback', '42000',
]


class ExtractionMessageSQLTests(SimpleTestCase):
    """core.db._extract_sql_message : tri métier / technique."""

    def _extrait(self, brut):
        return _extract_sql_message(pyodbc.Error('XXXXX', brut))

    def test_message_metier_transmis_intact(self):
        """Un RAISERROR applicatif (50000) garde son texte, sans bruit ODBC."""
        attendu = "Le numéro de l'enquêteur 1 doit être renseigné et supérieur à 0."
        with self.assertLogs('ever.db', level='ERROR') as capture:
            # Aucun log attendu ici : on en provoque un factice pour satisfaire
            # assertLogs, puis on vérifie qu'il est bien le seul.
            db.logger.error('sentinelle')
            obtenu = self._extrait(PREFIXE_ODBC + attendu + " (50000) (SQLMoreResults)")
        self.assertEqual(obtenu, attendu)
        self.assertEqual(len(capture.output), 1, "le cas métier ne doit rien journaliser")

    def test_erreur_systeme_conversion_masquee(self):
        """Une erreur système (241) ne doit pas remonter au client."""
        brut = (PREFIXE_ODBC + "Échec de la conversion d'une chaîne de caractères "
                "en date/heure. (241) (SQLExecDirectW)")
        with self.assertLogs('ever.db', level='ERROR'):
            obtenu = self._extrait(brut)
        self.assertNotIn('conversion', obtenu.lower())
        for marqueur in MARQUEURS_TECHNIQUES:
            self.assertNotIn(marqueur, obtenu)

    def test_violation_de_contrainte_masquee(self):
        """Le nom des objets de la base (table, contrainte) ne doit pas fuiter."""
        brut = (PREFIXE_ODBC + "Violation of PRIMARY KEY constraint "
                "'PK_Vacation_Zone'. Cannot insert duplicate key in object "
                "'dbo.Vacation_Zone'. (2627) (SQLExecDirectW)")
        with self.assertLogs('ever.db', level='ERROR'):
            obtenu = self._extrait(brut)
        self.assertNotIn('PK_Vacation_Zone', obtenu)
        self.assertNotIn('Vacation_Zone', obtenu)

    def test_format_inattendu_masque(self):
        """Un message qui ne suit pas le format attendu est masqué, pas tronqué."""
        brut = ("[08S01] [Microsoft][ODBC Driver 17 for SQL Server]"
                "TCP Provider: timeout expired")
        with self.assertLogs('ever.db', level='ERROR'):
            obtenu = self._extrait(brut)
        for marqueur in MARQUEURS_TECHNIQUES:
            self.assertNotIn(marqueur, obtenu)


class ReponseErreurAPITests(SimpleTestCase):
    """Rejoue le scénario exact de l'audit sur l'endpoint incriminé."""

    # URL testée par l'auditeur : le ' final fait échouer la conversion de date.
    PARAMS = {'date': "2026-06-16'", 'id_site': '', 'id_personne': '100029'}

    def _appel_en_erreur(self):
        exc = pyodbc.Error('42000', PREFIXE_ODBC +
                           "Échec de la conversion d'une chaîne de caractères "
                           "en date/heure. (241) (SQLExecDirectW)")
        requete = RequestFactory().get('/api/suivi/hors-aeroport/', self.PARAMS)
        requete.session = {
            'user_role': 'IFOP',
            'user_login': 'test',
            'user_code_societe_terrain': 'IFOP',
        }
        with patch.object(db, 'get_suivi_hors_aeroport', side_effect=exc):
            with self.assertLogs('ever.views', level='ERROR') as capture:
                # __wrapped__ : on court-circuite @login_required, hors sujet ici.
                reponse = views.api_suivi_hors_aeroport.__wrapped__(requete)
        return reponse, capture.output

    def test_aucune_information_technique_dans_la_reponse(self):
        reponse, _ = self._appel_en_erreur()
        corps = reponse.content.decode()
        self.assertEqual(reponse.status_code, 500)
        for marqueur in MARQUEURS_TECHNIQUES:
            self.assertNotIn(marqueur, corps,
                             f"fuite technique : « {marqueur} » présent dans la réponse")

    def test_reference_incident_presente_et_coherente(self):
        """La référence rendue au client doit permettre de retrouver le log."""
        import json
        reponse, logs = self._appel_en_erreur()
        charge = json.loads(reponse.content)
        reference = charge.get('ref')
        self.assertTrue(reference, "pas de référence d'incident dans la réponse")
        self.assertIn(reference, charge['message'])
        self.assertTrue(any(reference in ligne for ligne in logs),
                        "la référence rendue au client est absente des logs")

    def test_le_detail_technique_est_conserve_dans_les_logs(self):
        """Corollaire indispensable : on déplace l'information, on ne la perd pas."""
        _, logs = self._appel_en_erreur()
        journal = '\n'.join(logs)
        self.assertIn('ODBC Driver 17', journal)
        self.assertIn('Traceback', journal)
