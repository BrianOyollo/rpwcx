
 CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    contact VARCHAR(50),
    email VARCHAR(100) UNIQUE,
    user_type VARCHAR(20) CHECK (user_type IN ('admin', 'phlebotomist', 'supervisor', 'other')) NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tests (
    id SERIAL PRIMARY KEY,
    test_name VARCHAR(150) UNIQUE NOT NULL,
    description TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE requests (
    id SERIAL PRIMARY KEY,
    patient_name VARCHAR(100) NOT NULL,
    gender VARCHAR(10) CHECK (gender IN ('Male', 'Female', 'Other')),
    location TEXT NOT NULL,
    contact VARCHAR(50),
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled')),
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    assigned_to INTEGER REFERENCES users(id) ON DELETE SET NULL
);

-- note: split this table if this ever grows and you need to add test details, measurements, ...
-- for now, include test code in the name e.g U/E/C(123)
CREATE TABLE tests (
    id SERIAL PRIMARY KEY,
    category_name VARCHAR(100) UNIQUE NOT NULL,
    category_description TEXT,
    available_tests TEXT [] NOT NULL,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- CREATE TABLE test_categories (
--     id SERIAL PRIMARY KEY,
--     category_name VARCHAR(100) UNIQUE NOT NULL,
--     description TEXT
-- );

-- CREATE TABLE tests (
--     id SERIAL PRIMARY KEY,
--     test_name VARCHAR(150) UNIQUE NOT NULL,
--     category_id INT REFERENCES test_categories(id) ON DELETE CASCADE,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );

INSERT INTO tests (category_name, category_description, available_tests)
VALUES
-- HAEMOGRAM / HAEMATOLOGY
(
    'HAEMOGRAM/HAEMATOLOGY',
    'Haematology and complete blood count related tests.',
    ARRAY[
        'FBC only (CBC/FHG/TBC) [8890]',
        'ESR (Erythrocyte Sedimentation Rate) [5263]',
        'FBC + ESR [8891]',
        'Automated Reticulocyte Counts [9959]',
        'FBC + Retic + ESR [1307]',
        'PBF (Peripheral Blood Film) [6971]',
        'Blood Group & Rh Factor [2800]',
        'DU Test [9910]'
    ]
),

-- ANAEMIA / NUTRITION
(
    'ANAEMIA/NUTRITION',
    'Anaemia profile and nutritional biochemistry tests.',
    ARRAY[
        'Folate Levels (Serum) [4110]',
        'Folate RBC [6835]',
        'Iron studies (Iron Profile) (x6 Parameters) [6969]',
        'Transferrin Saturation (iron, Transferrin) [2717]',
        'UIBC (Measured) [5709]',
        'Vitamin A (Retinol) [9556]',
        'Vitamin B Profile (B1,B2,B3,B5,B6,B7) [4589]',
        'Vitamin B12 [4111]',
        'Vitamin C [8080]',
        'Vitamin E Alphatocopherol [7658]',
        'Vitamin K [9265]'
    ]
),

-- DIABETES / GLUCOSE METABOLISM
(
    'DIABETES/GLUCOSE METABOLISM',
    'Glucose regulation and diabetes diagnostic markers.',
    ARRAY[
        'Blood Glucose [1400]',
        'C-Peptide Level [9996]',
        'HbA1C (Glycosylated Hb) [4802]',
        'Insulin Levels [4160]',
        'Insulin Autoantibodies (IAA) [4137]',
        'IA2 Autoantibodies [9960]',
        'OGTT 75g [6893]',
        'Fructosamine [4425]',
        'GAD (Glutamic Acid Decarboxylase Ab) [5567]',
        'Ketones Serum [6142]',
        'UACR (Microalbuminuria) [7232]'
    ]
),

-- CARDIAC ASSAYS
(
    'CARDIAC ASSAYS',
    'Cardiac enzyme and cardiac biomarker tests.',
    ARRAY[
        'Cardiac Enzymes [1800]',
        'GDF-15 Cardiac Biomarker [6838]',
        'High Sensitivity CRP (hs-CRP) [A13407]',
        'Homocysteine Level [4132]',
        'pro-BNP (NT Pro BNP) [1811]',
        'Troponin I [4806]',
        'Troponin-T (High Sensitive) [1807]'
    ]
),

-- LIPID METABOLISM
(
    'LIPID METABOLISM',
    'Cholesterol and lipid profile markers.',
    ARRAY[
        'Lipoprotein (a) [1911]',
        'Apolipoprotein Profile (Apo A, Apo B) [6912]',
        'Lipid Profile (Cholesterol, Triglycerides, HDL, LDL) [1900]',
        'Lipid Profile Plus Apolipoproteins (x7 Parameters) [6913]'
    ]
),

-- INFLAMMATION / SEPSIS
(
    'INFLAMMATION/SEPSIS MARKERS',
    'Inflammatory and sepsis biomarkers.',
    ARRAY[
        'CRP Quantitative [4001]',
        'Ferritin - Inflammatory Marker [6834]',
        'IL-6 (Interleukin 6) [1061]',
        'Procalcitonin (PCT) [5042]'
    ]
),

-- KIDNEY FUNCTION
(
    'KIDNEY FUNCTION',
    'Renal and electrolyte function tests.',
    ARRAY[
        'Kidney Function Test (RFT) [1628]',
        'Creatinine with EGFR [1624]',
        'Cystatin C with EGFR [6806]',
        'Urea (BUN) [1601]',
        'Electrolytes (Na, K, Cl) [1700]',
        'Calcium Phosphate Profile [2806]',
        'Magnesium [1707]'
    ]
),

-- LIVER FUNCTION
(
    'LIVER FUNCTION',
    'Liver enzyme and bilirubin profile tests.',
    ARRAY[
        'LFT - Comprehensive (x10 Parameters) [1509]',
        'LFT - Basic (x7 Parameters) [7061]',
        'GLDH (Glutamate Dehydrogenase) [6818]',
        'LDH (Lactate Dehydrogenase) [1803]',
        'Bilirubin Profile (Total + Direct & Indirect) [1514]',
        'Ammonia (NH3) [1710]'
    ]
),

-- PANCREAS ASSAYS
(
    'PANCREAS ASSAYS',
    'Pancreatic enzyme tests.',
    ARRAY[
        'Amylase [2700]',
        'Lipase [2716]'
    ]
),

-- BONE ASSAYS
(
    'BONE ASSAYS',
    'Bone metabolism and mineral tests.',
    ARRAY[
        'Bone Biochemistry (ALP, Phosphate, Magnesium, Calcium - Corrected) [7108]',
        'Bone Profile Basic (x7 Parameters) [4453]',
        'Bone Turnover Markers (x9 Parameters) [7111]',
        'Calcium - Corrected [1749]',
        'Osteocalcin [6845]',
        'Parathyroid Hormone Intact (PTH) [4125]',
        'Vitamin D 25-OH [5050]'
    ]
),

-- ENDOCRINOLOGY
(
    'ENDOCRINOLOGY',
    'Endocrine and hormone regulation tests.',
    ARRAY[
        'ACTH (Adrenocorticotropic Hormone) [4119]',
        'ADH (Anti Diuretic Hormone) [6140]',
        'Aldosterone Renin Ratio (ARR) [6966]',
        'Cortisol [4112]',
        'Growth Hormone (GH) [4115]',
        'Insulin-like Growth Factor (IGF-1) [4187]',
        'Prolactin [4107]',
        'Dexamethasone Suppression Test [3248]',
        'Female Hormone Profile (With AMH) (x8 Parameters) [4145]',
        'Male Hormone Profile (With DHEA) (x10 Parameters) [1003]',
        'Testosterone (Total) [4124]',
        'Pituitary Hormone Profile (x10 Parameters) [4435]',
        'DHEA-S (Dehydroepiandrosterone Sulphate) [4120]',
        'Free Testosterone (calculated) (x4 Parameters) [6950]'
    ]
),

-- THYROID ASSAYS
(
    'THYROID ASSAYS',
    'Thyroid hormone and antibody tests.',
    ARRAY[
        'TFT Thyroid Function Test (FT3, FT4, TSH) [4100]',
        'Thyroglobulin Levels [7351]',
        'Thyroid Antibodies Profile (x3 Markers) [6996]',
        'TFT and Antibody Profile (x6 Parameters) [6995]',
        'Thyroid Hormone Uptake [6854]',
        'Free T4 Index [6983]'
    ]
),

-- COAGULATION / HEMOSTASIS
(
    'COAGULATION/HEMOSTASIS',
    'Coagulation, clotting factor and thrombosis tests.',
    ARRAY[
        'Coagulation Profile [4444]',
        'APTT [1306]',
        'PT/INR [1399]',
        'TT (Thrombin Time) [6926]',
        'Anti-Thrombin [1350]',
        'D-Dimer [1309]',
        'Factor IX [7002]',
        'FACTOR V Leiden Mutation [7007]',
        'Factor VIII [7001]',
        'Factor VIII Inhibitor Assay [4506]',
        'Factor X [7008]',
        'Fibrinogen Level [1308]',
        'Protein C and Free Protein S [9589]',
        'Thrombophilia Screen [9410]',
        'Von Willebrand Factor Antigen [8568]'
    ]
),

-- TUMOR MARKERS
(
    'TUMOR MARKERS',
    'Cancer and tumor-associated biomarkers.',
    ARRAY[
        'AFP (Alpha Fetoprotein) [4300]',
        'Beta hCG (Tumour Marker) [4309]',
        'CA 125 [4302]',
        'CA 15-3 [4305]',
        'CA 19-9 [4306]',
        'CA 72-4 [6831]',
        'CEA (Carcinoembryonic Antigen) [4301]',
        'Chromogranin A [8572]',
        'CYFRA 21-1 (Cytokeratin Fragment 21) [6644]',
        'Calcitonin [6840]',
        'NSE [6844]',
        'proGRP (SCLC lung tumor marker) [6849]',
        'SCC Squamous Cell Carcinoma Antigen [6645]',
        'PSA (Total) [4304]',
        'Free PSA / Total PSA Ratio [6836]',
        'Plasma Metanephrines [7873]'
    ]
);

