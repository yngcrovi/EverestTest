CREATE TABLE IF NOT EXISTS people (
    id BIGINT PRIMARY KEY,
    fio text NOT NULL,
    create_dt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    inn VARCHAR(100) GENERATED ALWAYS AS ('ИНН ' || id::text) STORED,
    path TEXT NOT NULL,
    link TEXT GENERATED ALWAYS AS ('https://fedresurs.ru' || path) STORED
);

CREATE TABLE IF NOT EXISTS bankruptcy_info (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    inn BIGINT NOT NULL, 
    case_num VARCHAR(100),
    last_bankruptcy_dt DATE,
    create_dt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_bankruptcy_people 
    FOREIGN KEY (inn) 
    REFERENCES people(id)
    ON DELETE CASCADE,  -- Что делать при удалении записи из people

    CONSTRAINT unique_bankruptcy_info UNIQUE (inn, case_num)
);

CREATE TABLE IF NOT EXISTS bankruptcy_docs_data (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    case_num_id uuid NOT NULL, 
    last_dt  date NOT NULL,
    docs_name text NOT NULL,
    link text NOT NULL,
    create_dt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_bankruptcy_info
    FOREIGN KEY (case_num_id) 
    REFERENCES bankruptcy_info(id)
    ON DELETE CASCADE,

    CONSTRAINT unique_bankruptcy_data UNIQUE (case_num_id, last_dt, docs_name)
);

CREATE INDEX idx_bankruptcy_info_inn ON bankruptcy_info(inn);
CREATE INDEX idx_bankruptcy_data_case_num_oid ON bankruptcy_docs_data(case_num_id);