
/*
    # Notes on Current Schema Design

The schema is intentionally simple and slightly denormalized. This is by design, given the expected usage:
    - User count is small, so extensive normalization (separate profiles, contacts, roles table, etc.) is not necessary right now.
    - The current setup keeps development fast and maintenance easy.
    - Tables like tests and requests store arrays (TEXT[]) for convenience. This works well at small scale and avoids extra join tables at this stage.

If the system grows in the future—more users, more test categories, analytics needs, or heavier querying—then it would make sense to:
    - Normalize tests into 1:Many and Many:Many join tables.
    - Split user roles into a separate lookup table.

For now, the schema is intentionally “lightweight” and fits the expected scale.

*/

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    dkl_code VARCHAR(20) UNIQUE,
    name VARCHAR(100) NOT NULL,
    contact VARCHAR(50),
    email VARCHAR(100) UNIQUE,
    user_type VARCHAR(20) CHECK (user_type IN ('admin', 'phlebotomist', 'supervisor','doctor', 'other')) NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE requests (
    id SERIAL PRIMARY KEY,

    first_name VARCHAR(100),
    surname VARCHAR(100),
    middle_name VARCHAR(100),
    dob DATE,
    gender VARCHAR(20),
    phone VARCHAR(15),
    email VARCHAR(150),
    location VARCHAR(150),

    doctor_dkl_code VARCHAR REFERENCES users(dkl_code),

    selected_tests TEXT[] NOT NULL,

    assign_to VARCHAR REFERENCES users(dkl_code) NOT NULL, 
    priority VARCHAR(20) CHECK (priority IN ('Urgent', 'Routine')) DEFAULT 'Routine',

    collection_date DATE,
    collection_time TIME,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE tests (
    id SERIAL PRIMARY KEY,
    category_name VARCHAR(100) UNIQUE NOT NULL,
    category_description TEXT,
    available_tests TEXT [] NOT NULL,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


