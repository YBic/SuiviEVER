-- ============================================================
-- Journal des connexions / déconnexions EVER 2026
-- À exécuter une seule fois sur EVER_DEV puis sur EVER (prod)
-- ============================================================

-- Table -----------------------------------------------------------
IF NOT EXISTS (
    SELECT 1 FROM sys.objects WHERE name = 'Log_Connexion' AND type = 'U'
)
BEGIN
    CREATE TABLE dbo.Log_Connexion (
        ID_Log_Connexion  INT           IDENTITY(1,1) NOT NULL,
        ID_Utilisateur    SMALLINT      NOT NULL,
        Action            VARCHAR(10)   NOT NULL,
        Date_Action       DATETIME      NOT NULL
            CONSTRAINT DF_Log_Connexion_Date_Action DEFAULT GETDATE(),
        IP_Adresse        VARCHAR(50)   NULL,

        CONSTRAINT PK_Log_Connexion
            PRIMARY KEY CLUSTERED (ID_Log_Connexion),

        CONSTRAINT FK_Log_Connexion_Utilisateur
            FOREIGN KEY (ID_Utilisateur)
            REFERENCES dbo.Utilisateur (ID_Utilisateur),

        CONSTRAINT Chk_Log_Connexion_Action
            CHECK (Action IN ('LOGIN', 'LOGOUT'))
    );

    PRINT 'Table Log_Connexion créée.';
END
ELSE
    PRINT 'Table Log_Connexion déjà existante — ignorée.';
GO

-- Procédure stockée -----------------------------------------------
IF OBJECT_ID('dbo.ft_EVER_Log_Connexion', 'P') IS NOT NULL
    DROP PROCEDURE dbo.ft_EVER_Log_Connexion;
GO

CREATE PROCEDURE dbo.ft_EVER_Log_Connexion
    @Id_Personne   INT,
    @Action        VARCHAR(10),
    @IP_Adresse    VARCHAR(50) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    -- Insertion silencieuse : un échec de log ne doit jamais bloquer la navigation
    BEGIN TRY
        INSERT INTO dbo.Log_Connexion (ID_Utilisateur, Action, IP_Adresse)
        VALUES (@Id_Personne, @Action, @IP_Adresse);
    END TRY
    BEGIN CATCH
        -- Absorbe l'erreur sans la propager
    END CATCH
END;
GO

PRINT 'SP ft_EVER_Log_Connexion créée.';
