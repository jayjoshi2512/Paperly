# Paperly — MySQL Schema

> MySQL 8.0 | Database: `paperly` | Charset: utf8mb4

## Setup
```sql
CREATE DATABASE paperly CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'paperly_user'@'%' IDENTIFIED BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON paperly.* TO 'paperly_user'@'%';
FLUSH PRIVILEGES;
```

## Tables

### workspaces
```sql
CREATE TABLE workspaces (
    id          CHAR(36)     NOT NULL DEFAULT (UUID()),
    name        VARCHAR(255) NOT NULL,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
) ENGINE=InnoDB;
```

### users
```sql
CREATE TABLE users (
    id            CHAR(36)     NOT NULL DEFAULT (UUID()),
    workspace_id  CHAR(36)     NOT NULL,
    email         VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role          ENUM('admin','member') NOT NULL DEFAULT 'member',
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_email (email),
    CONSTRAINT fk_users_workspace FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id) ON DELETE CASCADE
) ENGINE=InnoDB;
```

### documents
```sql
CREATE TABLE documents (
    id                CHAR(36)     NOT NULL DEFAULT (UUID()),
    workspace_id      CHAR(36)     NOT NULL,
    uploaded_by       CHAR(36)     NOT NULL,
    filename          VARCHAR(500) NOT NULL,
    file_size_bytes   INT UNSIGNED,
    page_count        INT UNSIGNED,
    chunking_strategy ENUM('fixed','recursive','semantic') NOT NULL DEFAULT 'recursive',
    chunk_count       INT UNSIGNED,
    status            ENUM('processing','ready','failed') NOT NULL DEFAULT 'processing',
    version           TINYINT UNSIGNED NOT NULL DEFAULT 1,
    created_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_workspace (workspace_id),
    CONSTRAINT fk_docs_workspace FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_docs_user FOREIGN KEY (uploaded_by)
        REFERENCES users(id)
) ENGINE=InnoDB;
```

### chunks
```sql
CREATE TABLE chunks (
    id              CHAR(36)  NOT NULL DEFAULT (UUID()),
    document_id     CHAR(36)  NOT NULL,
    qdrant_point_id CHAR(36)  NOT NULL,
    chunk_index     INT UNSIGNED NOT NULL,
    page_number     INT UNSIGNED,
    token_count     INT UNSIGNED,
    chunk_text      TEXT      NOT NULL,
    created_at      DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_document (document_id),
    FULLTEXT idx_ft_text (chunk_text),
    CONSTRAINT fk_chunks_doc FOREIGN KEY (document_id)
        REFERENCES documents(id) ON DELETE CASCADE
) ENGINE=InnoDB;
```

### queries
```sql
CREATE TABLE queries (
    id                  CHAR(36)   NOT NULL DEFAULT (UUID()),
    workspace_id        CHAR(36)   NOT NULL,
    user_id             CHAR(36)   NOT NULL,
    query_text          TEXT       NOT NULL,
    answer_text         TEXT,
    retrieved_chunk_ids JSON,
    was_answered        TINYINT(1) NOT NULL DEFAULT 1,
    faithfulness_score  FLOAT,
    relevancy_score     FLOAT,
    latency_ms          INT UNSIGNED,
    created_at          DATETIME   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_workspace_time (workspace_id, created_at),
    INDEX idx_user (user_id),
    CONSTRAINT fk_queries_workspace FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_queries_user FOREIGN KEY (user_id)
        REFERENCES users(id)
) ENGINE=InnoDB;
```

### unanswered_queries
```sql
CREATE TABLE unanswered_queries (
    id            CHAR(36)     NOT NULL DEFAULT (UUID()),
    workspace_id  CHAR(36)     NOT NULL,
    query_text    TEXT         NOT NULL,
    cluster_label VARCHAR(255),
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_workspace (workspace_id),
    CONSTRAINT fk_unanswered_workspace FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id) ON DELETE CASCADE
) ENGINE=InnoDB;
```

### document_diffs
```sql
CREATE TABLE document_diffs (
    id           CHAR(36)       NOT NULL DEFAULT (UUID()),
    document_id  CHAR(36)       NOT NULL,
    from_version TINYINT UNSIGNED NOT NULL,
    to_version   TINYINT UNSIGNED NOT NULL,
    diff_summary JSON,
    created_at   DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT fk_diffs_doc FOREIGN KEY (document_id)
        REFERENCES documents(id) ON DELETE CASCADE
) ENGINE=InnoDB;
```
