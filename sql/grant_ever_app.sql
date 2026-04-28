-- ============================================================
-- Droits du compte applicatif ever_app sur EVER_DEV / EVER
-- À exécuter par un administrateur SQL Server
-- ============================================================

USE [EVER_DEV];   -- remplacer par [EVER] pour la prod
GO

-- Lecture de toutes les tables et vues du schéma dbo
GRANT SELECT  ON SCHEMA::dbo TO ever_app;

-- Exécution de toutes les fonctions et procédures du schéma dbo
GRANT EXECUTE ON SCHEMA::dbo TO ever_app;

-- Écriture sur la table de journalisation (INSERT uniquement)
GRANT INSERT  ON dbo.Log_Connexion TO ever_app;

-- Mise à jour du mot de passe utilisateur (UPDATE sur une seule colonne)
GRANT UPDATE  ON dbo.Utilisateur (Mot_de_Passe) TO ever_app;

GO

-- Vérification rapide
SELECT
    dp.class_desc,
    OBJECT_NAME(dp.major_id)   AS objet,
    dp.permission_name,
    dp.state_desc
FROM sys.database_permissions dp
WHERE dp.grantee_principal_id = USER_ID('ever_app')
ORDER BY dp.class_desc, objet, dp.permission_name;
