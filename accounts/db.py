"""
Accès SQL Server pour l'authentification – EVER 2026.

Objets SQL utilisés :
  - ft_EVER_Liste_Utilisateur(@pUtilisateur_Login)  → lecture profil utilisateur
  - UPDATE direct sur dbo.Utilisateur               → définition / réinitialisation du mot de passe
    (à terme : Prc_Utilisateur_Mot_De_Passe_Update si la BDD expose une SP dédiée)

Convention de hash : SHA-256 hexadécimal (64 caractères) stocké dans Utilisateur.Mot_de_Passe (nvarchar).
NULL dans ce champ = première connexion, le site demande la création d'un mot de passe.
Réinitialisation admin = remettre le champ à NULL directement en base.
"""

import hashlib
import hmac
import pyodbc
from django.conf import settings


# ---------------------------------------------------------------------------
# Connexion
# ---------------------------------------------------------------------------

def get_connection():
    cfg = settings.DB_CONNECTION
    conn_str = (
        f"DRIVER={cfg['DRIVER']};"
        f"SERVER={cfg['SERVER']};"
        f"DATABASE={cfg['DATABASE']};"
        f"TrustServerCertificate={cfg['TrustServerCertificate']};"
    )
    if cfg.get('UID'):
        # Les accolades {} sont requises si le mot de passe contient des
        # caractères spéciaux ODBC (;  {  }). On les applique systématiquement.
        pwd = cfg['PWD'].replace('}', '}}')   # échappe les } internes
        conn_str += f"UID={cfg['UID']};PWD={{{pwd}}};"
    else:
        conn_str += "Trusted_Connection=yes;"
    return pyodbc.connect(conn_str)


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Retourne le hash SHA-256 hex du mot de passe fourni."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


# ---------------------------------------------------------------------------
# Lecture du profil utilisateur
# ---------------------------------------------------------------------------

def get_utilisateur(login: str) -> dict | None:
    """
    Appelle ft_EVER_Utilisateur(@pUtilisateur_Login).
    Retourne un dict ou None si le login n'existe pas.

    Colonnes retournées par la fonction :
        ID_Utilisateur, Utilisateur_Login, Nom, Prenom,
        Mot_De_Passe_Hash,          ← NULL = première connexion
        ID_Role, Code_Role,
        ID_Societe_Terrain, Code_Societe_Terrain
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM dbo.ft_EVER_Utilisateur(?)",
                (login,)
            )
            row = cursor.fetchone()
            if row is None:
                return None
            columns = [col[0] for col in cursor.description]
            return dict(zip(columns, row))
    except pyodbc.Error:
        return None


# ---------------------------------------------------------------------------
# Authentification complète
# ---------------------------------------------------------------------------

class AuthResult:
    """Résultats possibles d'une tentative de connexion."""
    OK = 'ok'                        # connexion réussie
    UNKNOWN = 'unknown'              # login introuvable
    FIRST_LOGIN = 'first_login'      # mot de passe non encore défini
    BAD_PASSWORD = 'bad_password'    # mot de passe incorrect


def authenticate(login: str, password: str) -> tuple[str, dict | None]:
    """
    Tente d'authentifier un utilisateur.

    Retourne (AuthResult.*, user_dict | None).

    Flux :
        1. Appel ft_EVER_Liste_Utilisateur → si aucune ligne : UNKNOWN
        2. Mot_De_Passe_Hash IS NULL → FIRST_LOGIN  (créer le mdp)
        3. hash(password) == Mot_De_Passe_Hash → OK
        4. Sinon → BAD_PASSWORD
    """
    user = get_utilisateur(login)
    if user is None:
        return AuthResult.UNKNOWN, None

    stored_hash = user.get('Mot_De_Passe_Hash')

    if stored_hash is None:
        # Première connexion : seul le mot de passe générique est accepté
        first_login_pwd = getattr(settings, 'FIRST_LOGIN_PASSWORD', '')
        if hmac.compare_digest(password, first_login_pwd):
            return AuthResult.FIRST_LOGIN, user
        return AuthResult.BAD_PASSWORD, None

    if hash_password(password) == stored_hash:
        return AuthResult.OK, user

    return AuthResult.BAD_PASSWORD, None


# ---------------------------------------------------------------------------
# Création / mise à jour du mot de passe
# ---------------------------------------------------------------------------

def set_password(login: str, new_password: str) -> bool:
    """
    Enregistre le hash SHA-256 du nouveau mot de passe dans Utilisateur.Mot_de_Passe.
    Appelée lors de la première connexion ou d'une redéfinition volontaire.

    Retourne True si la mise à jour a réussi, False sinon.

    Note : l'administrateur peut remettre Mot_de_Passe = NULL directement en base
    pour forcer un utilisateur à redéfinir son mot de passe à la prochaine connexion.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE dbo.Utilisateur
                SET    Mot_de_Passe = ?
                WHERE  Utilisateur_Login = ?
                """,
                (hash_password(new_password), login)
            )
            conn.commit()
            return cursor.rowcount == 1
    except pyodbc.Error:
        return False


# ---------------------------------------------------------------------------
# Journalisation des connexions / déconnexions
# ---------------------------------------------------------------------------

def log_connexion(id_utilisateur: int, action: str, ip: str | None = None) -> None:
    """
    Appelle ft_EVER_Log_Connexion(@Id_Personne, @Action, @IP_Adresse).
    Absorbe silencieusement toute erreur : un échec de log ne doit jamais
    bloquer la navigation.

    action : 'LOGIN' | 'LOGOUT'
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "EXEC dbo.ft_EVER_Log_Connexion ?,?,?",
                (id_utilisateur, action, ip)
            )
            conn.commit()
    except Exception:
        pass  # silencieux par spec
