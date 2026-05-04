# Cartographie TVFs / Procédures stockées → API → Pages

> Document de référence pour les intervenants SQL Server (Philippe).
> Mis à jour : mai 2026.

---

## Conventions

- Tous les paramètres acceptent `NULL` (filtres optionnels) sauf indication contraire.
- Les TVFs sont appelées via `SELECT * FROM dbo.fn(...)` — jamais `EXEC`.
- Les noms de colonnes SQL (français, avec accents/espaces) sont normalisés en Python
  avant d'être exposés en JSON. Les colonnes JSON sont celles consommées par le JS.
- `ID_Societe_Terrain` : **1 = IFOP**, **2 = Solutions Terrain**.

---

## 1. Authentification

### `ft_EVER_Utilisateur(@pLogin varchar)`

| Paramètre | Type | Nullable |
|-----------|------|----------|
| `@pLogin` | `varchar` | non |

**Colonnes utilisées :**

| Colonne SQL | Clé session Django |
|-------------|-------------------|
| `ID_Utilisateur` | — |
| `Utilisateur_Login` | `user_login` |
| `Nom` | `user_nom` |
| `Prenom` | `user_prenom` |
| `Mot_De_Passe_Hash` | (comparaison bcrypt) |
| `ID_Role` | — |
| `Code_Role` | `user_role` |
| `ID_Societe_Terrain` | `user_id_societe_terrain` |
| `Code_Societe_Terrain` | — |

**Endpoint :** login (`POST /login/`)

---

## 2. Listes de référence (dropdowns filtres)

### `ft_EVER_Liste_Aeroports_Vacation`

```
@pUtilisateur_Login   varchar   NULL ok
@pID_Societe_Terrain  tinyint   NULL ok
@pDate_Debut          date      NULL ok
@pDate_Fin            date      NULL ok
```

**Colonnes utilisées → JSON :**

| SQL | JSON |
|-----|------|
| `ID_Aeroport` | `Id_Aeroport` |
| `Code_Aeroport` | `Code_Aeroport` |
| `Nom_Aeroport` | `Nom_Aeroport` |

**Endpoint :** `GET /api/aeroports/?date=YYYY-MM-DD`
**Pages :** Suivi Aéroport, Affectation

---

### `ft_EVER_Liste_Enqueteur_Date_Aeroport`

```
@pID_Societe_Terrain    tinyint   NULL ok
@pDate_Debut            date      NULL ok
@pDate_Fin              date      NULL ok
@pID_Aeroport           smallint  NULL ok
@pID_Type_Vacation_Vol  tinyint   NULL ok
```

**Colonnes utilisées → JSON :**

| SQL | JSON |
|-----|------|
| `ID_Personne` | `Id_Personne` |
| `Libelle_Enqueteur` | `Libelle_Enqueteur` |

**Endpoint :** `GET /api/enqueteurs/aeroport/?date=&id_aeroport=`
**Pages :** Suivi Aéroport (filtre enquêteur)

---

### `ft_EVER_Liste_Enqueteurs_Aeroport`

```
@pID_Societe_Terrain  tinyint   NULL ok
@pMatricule           varchar   NULL ok
```

**Colonnes retournées :** `Matricule`, `ID_Personne`, `Nom`, `Prenom`, `ID_Role`, `Code_Role`

**Colonnes utilisées → JSON :**

| Calcul Python | JSON |
|---------------|------|
| `ID_Personne` | `Id_Personne` |
| `f"{Matricule} – {Prenom} {Nom}"` | `Libelle_Enqueteur` |

**Endpoint :** `GET /api/affectation/enqueteurs/`
**Pages :** Affectation (dropdown enquêteur dans chaque ligne vacation)

---

## 3. Tableau de suivi aéroport

### `ft_EVER_Tableau_Chef_Equipe`

```
@pUtilisateur_Login     varchar   NULL ok
@pID_Societe_Terrain    tinyint   NULL ok
@pDate_Vol              date      NULL ok
@pID_Aeroport           smallint  NULL ok
@pID_Type_Vacation_Vol  tinyint   NULL ok
@pID_ENPA_VolSplit       int       toujours NULL côté web
@pID_Personne           int       NULL ok
@pDuree_Minute_Cloture  int       toujours NULL côté web
```

> ⚠️ La TVF retourne des lignes vacation **et** des lignes de sous-totaux (TOTAL VOL,
> TOTAL AÉROPORT). Python filtre sur `ID_Vacation_Vol IS NOT NULL` pour ne garder
> que les lignes vacation — le JS recalcule ses propres totaux.

**Colonnes SQL → JSON (normalisées en Python) :**

| Colonne SQL | Clé JSON |
|-------------|----------|
| `ID_Vacation_Vol` | `ID_Vacation_Vol` |
| `ID_Vacation_Enqueteur` | `ID_Vacation_Enqueteur` |
| `ID_Personne` | `ID_Personne` |
| `Rang_Enqueteur` | `Rang_Enqueteur` |
| `Code Aéroport Départ` | `Code_Aeroport` |
| `ID_Aeroport` → lookup `dbo.Aeroport` | `Nom_Aeroport` |
| `N° Vacation` | `Numero_Vacation` |
| `N° Vol` | `Numero_Vol` |
| `N° Vol` (avant "-") | `Code_Compagnie` |
| `Compagnie` | `Nom_Compagnie` |
| `Enquêteur` | `Libelle_Enqueteur` |
| `Destination` | `Aeroport_Destination` |
| `Heure départ (Théorique)` | `Heure_Depart` |
| `Objectif Questionnaires` | `Objectif` |
| `100% Completés` | `Completes_100` |
| `Recrutés` | `Recrutes` |
| `Completés Questions FAF` | `Questionnaires_Valides` |
| `Abandon` | `Abandons` |
| `STATUT VOL` | `Statut_Vol` |
| `Commentaires_Vacation` | `Commentaire_Vacation` |
| `Commentaires_Vacation_Vol` | `Commentaire_Vol` |

**Endpoint :** `GET /api/suivi/aeroport/?date=&id_aeroport=&id_personne=&id_type_vol=`
**Page :** Suivi Aéroport

---

## 4. Tableau de suivi hors aéroport

### `ft_Extranet_Vacation_Zone`

```
@pID_Societe_Terrain  tinyint   NULL ok
@pID_Vacation_Zone    int       NULL ok
@pID_Zone_Enquete     smallint  NULL ok   ← filtre "site"
@pID_Type_Site        tinyint   NULL ok
@pID_Site             smallint  NULL ok
@pDate_Vacation_Debut date      NULL ok
@pDate_Vacation_Fin   date      NULL ok
@pNumero_Enqueteur    tinyint   NULL ok
@pNumero_Vacation     tinyint   NULL ok
@pID_Enqueteur        int       NULL ok   ← filtre "enquêteur"
```

> ℹ️ Retourne une ligne par (vacation × enquêteur). Python ne garde que
> `Numero_Enqueteur = 1` pour éviter le double-comptage des objectifs.

**Colonnes SQL → JSON :**

| Colonne SQL | Clé JSON |
|-------------|----------|
| `ID_Zone_Enquete` | `Id_Site` |
| `Zone_Enquete` | `Nom_Site` |
| *(hardcodé)* | `Type_Site` = `'ZONE'` |
| `ID_Vacation_Zone` | `ID_Vacation` |
| `Numero_Vacation` | `Numero_Vacation` |
| `Enqueteur` | `Libelle_Enqueteur` |
| `Date_Vacation` | `Date_Vacation` (str YYYY-MM-DD) |
| `Nbre_Interviews_A_Faire` | `Objectif` |
| `Nbre_Interviews_Realisees_Valides` | `Completes_100` |
| `Nbre_Interviews_Realisees` | `Recrutes` |
| `Nbre_Interviews_FAF_Realisees_Valides` | `Questionnaires_Valides` |
| `Recrutes - Valides` *(calculé)* | `Abandons` |
| `Commentaire_Avant_Vacation` | `Commentaire_Vacation` |
| `Affectation_Modifiable` | `Affectation_Modifiable` |

**Endpoints :**

| Endpoint | Paramètres TVF utilisés |
|----------|------------------------|
| `GET /api/suivi/hors-aeroport/` | `ID_Societe_Terrain`, `ID_Zone_Enquete`, dates, `ID_Enqueteur` |
| `GET /api/sites/` | `ID_Societe_Terrain`, dates, `ID_Enqueteur` → dédoublonnage par zone |
| `GET /api/enqueteurs/site/` | `ID_Societe_Terrain`, `ID_Zone_Enquete`, dates → dédoublonnage par enquêteur |

**Page :** Suivi Hors Aéroport

---

## 5. Affectation

### `ft_EVER_Liste_Aeroports_Affectation`

```
@pID_Societe_Terrain  tinyint  NULL ok
@pDate_Debut          date     NULL ok
@pDate_Fin            date     NULL ok
```

Retourne les aéroports disponibles pour la page affectation.
*(Colonnes : à confirmer — non chiffrée)*

---

### `ft_Extranet_Vacation_Aeroport_Pivot`

```
@pID_Societe_Terrain   tinyint   NULL ok
@pID_Aeroport          smallint  NULL ok
@pDate_Vacation_Debut  date      NULL ok
@pDate_Vacation_Fin    date      NULL ok
@pNumero_Vacation      varchar   toujours NULL côté web
@pID_Personne          int       NULL ok
```

> ⚠️ Retourne des objets `datetime.date` et `datetime.time` (non JSON-sérialisables).
> Python les convertit en chaînes avant l'envoi.

**Colonnes SQL → JSON :**

| Colonne SQL | Clé JSON |
|-------------|----------|
| `ID_Vacation_Enqueteur_1` | `ID_Vacation` |
| `Nom_Aeroport` | `Nom_Site_Ou_Aeroport` |
| `Date_Vacation` *(date)* | `Date_Vacation` (str YYYY-MM-DD) |
| `Code_Periode_Journee` | `Code_Periode_Journee` |
| `Numero_Vacation` | `Numero_Vacation` |
| `Heure_Arrivee_Enqueteur` *(time/timedelta)* | `Heure_Arrivee_Enqueteur` (str HH:MM) |
| `Heure_Depart_Enqueteur` *(time/timedelta)* | `Heure_Depart_Enqueteur` (str HH:MM) |
| `Nbre_Interviews_A_Faire` | `Nbre_Interviews_A_Faire` |
| `Nbre_Interviews_Realisees` | `Nbre_Interviews_Realisees` |
| `Nbre_Interviews_Realisees_Valides` | `Nbre_Interviews_Valides` |
| `ID_Personne_1` | `ID_Personne_1` |
| `ID_Personne_2` | `ID_Personne_2` |
| `Commentaire_Avant_Vacation` | `Commentaire_Avant` |
| `Commentaire_Apres_Vacation` | `Commentaire_Apres` |
| `Affectation_Modifiable` | `Affectation_Modifiable` |

**Endpoint :** `GET /api/affectation/vacations/?date=&id_aeroport=&id_personne=`
**Page :** Affectation

---

## 6. Procédures stockées (écriture)

### `Prc_Vacation_Aeroport_Affectation`

```
@pID_Vacation_Enqueteur  int
@pID_Personne            int    NULL = désaffectation
@pMode_Extranet          bit    = 1  (toujours)
```

**Endpoint :** `POST /api/affectation/set/`
**Action :** Affecter ou désaffecter un enquêteur à une vacation.

---

### `Prc_Vacation_Aeroport_Commentaire_Update`

```
@pID_Vacation_Vol          int
@pCommentaire_Vac_Enq_1    nvarchar   NULL ok
@pCommentaire_Vol_Enq_1    nvarchar   NULL ok
@pCommentaire_Vac_Enq_2    NULL       toujours NULL côté web
@pCommentaire_Vol_Enq_2    NULL       toujours NULL côté web
@pMatricule_Connexion      varchar
@pMode_Extranet            bit        = 1  (toujours)
```

**Endpoint :** `POST /api/commentaire/`
**Action :** Créer ou mettre à jour le commentaire avant/après vacation.

---

## 7. TVFs en attente (placeholders)

| TVF | Endpoint concerné | État |
|-----|------------------|------|
| TVF hors aéroport détail | `GET /api/suivi/hors-aeroport/detail/` | À créer par Philippe |

---

## Points d'attention pour Philippe

1. **Noms de colonnes** — Toute modification d'un nom de colonne (accents, espaces, casse)
   dans une TVF existante casse le mapping Python sans lever d'erreur visible côté SQL.
   Prévenir l'équipe dev avant tout renommage.

2. **Lignes de sous-totaux** — `ft_EVER_Tableau_Chef_Equipe` retourne des lignes "TOTAL VOL"
   et "TOTAL AÉROPORT" mélangées aux lignes vacation. Le filtre Python repose sur
   `ID_Vacation_Vol IS NOT NULL` pour les écarter. Si d'autres TVFs adoptent ce pattern,
   le documenter ici.

3. **Types datetime** — Les colonnes `date` et `time` de SQL Server arrivent en Python comme
   objets `datetime.date` / `datetime.time` ou `datetime.timedelta` (selon le driver ODBC).
   Ils ne sont pas JSON-sérialisables nativement — penser à le signaler si une nouvelle TVF
   expose ce type de colonnes.

4. **Chiffrement** — Les TVFs chiffrées (`WITH ENCRYPTION`) empêchent toute inspection du
   code SQL depuis l'application. Conserver une copie déchiffrée dans un script de référence
   accessible à Philippe.
