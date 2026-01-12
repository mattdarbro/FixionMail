-- Character Names Database for FixionMail
-- Run this in your Supabase SQL Editor

-- Create the character_names table
CREATE TABLE IF NOT EXISTS public.character_names (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    name_type TEXT NOT NULL CHECK (name_type IN ('first', 'last')),
    gender TEXT CHECK (gender IN ('male', 'female', 'neutral')),
    cultural_origin TEXT NOT NULL,
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Prevent duplicate names within same type/gender/culture
    UNIQUE(name, name_type, gender, cultural_origin)
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_character_names_type ON public.character_names(name_type);
CREATE INDEX IF NOT EXISTS idx_character_names_gender ON public.character_names(gender);
CREATE INDEX IF NOT EXISTS idx_character_names_origin ON public.character_names(cultural_origin);
CREATE INDEX IF NOT EXISTS idx_character_names_usage ON public.character_names(usage_count);

-- Enable RLS
ALTER TABLE public.character_names ENABLE ROW LEVEL SECURITY;

-- Allow service role full access
CREATE POLICY "Service role has full access to character_names"
    ON public.character_names
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Seed with diverse names
-- First Names - Male
INSERT INTO public.character_names (name, name_type, gender, cultural_origin) VALUES
-- English/American
('James', 'first', 'male', 'english'), ('William', 'first', 'male', 'english'),
('Henry', 'first', 'male', 'english'), ('Thomas', 'first', 'male', 'english'),
('Edward', 'first', 'male', 'english'), ('Charles', 'first', 'male', 'english'),
('George', 'first', 'male', 'english'), ('Richard', 'first', 'male', 'english'),
('Robert', 'first', 'male', 'english'), ('Michael', 'first', 'male', 'english'),
('David', 'first', 'male', 'english'), ('Daniel', 'first', 'male', 'english'),
('Matthew', 'first', 'male', 'english'), ('Andrew', 'first', 'male', 'english'),
('Benjamin', 'first', 'male', 'english'), ('Samuel', 'first', 'male', 'english'),
('Nathan', 'first', 'male', 'english'), ('Oliver', 'first', 'male', 'english'),
('Alexander', 'first', 'male', 'english'), ('Christopher', 'first', 'male', 'english'),
-- Irish
('Liam', 'first', 'male', 'irish'), ('Sean', 'first', 'male', 'irish'),
('Patrick', 'first', 'male', 'irish'), ('Brendan', 'first', 'male', 'irish'),
('Declan', 'first', 'male', 'irish'), ('Finn', 'first', 'male', 'irish'),
('Cian', 'first', 'male', 'irish'), ('Connor', 'first', 'male', 'irish'),
-- Spanish
('Miguel', 'first', 'male', 'spanish'), ('Carlos', 'first', 'male', 'spanish'),
('Diego', 'first', 'male', 'spanish'), ('Rafael', 'first', 'male', 'spanish'),
('Antonio', 'first', 'male', 'spanish'), ('Luis', 'first', 'male', 'spanish'),
('Alejandro', 'first', 'male', 'spanish'), ('Javier', 'first', 'male', 'spanish'),
-- Italian
('Marco', 'first', 'male', 'italian'), ('Giuseppe', 'first', 'male', 'italian'),
('Lorenzo', 'first', 'male', 'italian'), ('Francesco', 'first', 'male', 'italian'),
('Luca', 'first', 'male', 'italian'), ('Giovanni', 'first', 'male', 'italian'),
-- French
('Pierre', 'first', 'male', 'french'), ('Jean', 'first', 'male', 'french'),
('Louis', 'first', 'male', 'french'), ('Henri', 'first', 'male', 'french'),
('Antoine', 'first', 'male', 'french'), ('Philippe', 'first', 'male', 'french'),
-- German
('Hans', 'first', 'male', 'german'), ('Friedrich', 'first', 'male', 'german'),
('Wilhelm', 'first', 'male', 'german'), ('Karl', 'first', 'male', 'german'),
('Stefan', 'first', 'male', 'german'), ('Maximilian', 'first', 'male', 'german'),
-- Scandinavian
('Erik', 'first', 'male', 'scandinavian'), ('Lars', 'first', 'male', 'scandinavian'),
('Magnus', 'first', 'male', 'scandinavian'), ('Bjorn', 'first', 'male', 'scandinavian'),
('Anders', 'first', 'male', 'scandinavian'), ('Sven', 'first', 'male', 'scandinavian'),
-- Japanese
('Kenji', 'first', 'male', 'japanese'), ('Hiroshi', 'first', 'male', 'japanese'),
('Takeshi', 'first', 'male', 'japanese'), ('Yuki', 'first', 'male', 'japanese'),
('Ryu', 'first', 'male', 'japanese'), ('Akira', 'first', 'male', 'japanese'),
-- Chinese
('Wei', 'first', 'male', 'chinese'), ('Chen', 'first', 'male', 'chinese'),
('Ming', 'first', 'male', 'chinese'), ('Jun', 'first', 'male', 'chinese'),
('Kai', 'first', 'male', 'chinese'), ('Lei', 'first', 'male', 'chinese'),
-- Indian
('Raj', 'first', 'male', 'indian'), ('Vikram', 'first', 'male', 'indian'),
('Arjun', 'first', 'male', 'indian'), ('Sanjay', 'first', 'male', 'indian'),
('Rohan', 'first', 'male', 'indian'), ('Aditya', 'first', 'male', 'indian'),
-- Arabic
('Omar', 'first', 'male', 'arabic'), ('Hassan', 'first', 'male', 'arabic'),
('Khalid', 'first', 'male', 'arabic'), ('Ahmed', 'first', 'male', 'arabic'),
('Yusuf', 'first', 'male', 'arabic'), ('Tariq', 'first', 'male', 'arabic'),
-- African
('Kwame', 'first', 'male', 'african'), ('Kofi', 'first', 'male', 'african'),
('Jabari', 'first', 'male', 'african'), ('Amari', 'first', 'male', 'african'),
('Zuberi', 'first', 'male', 'african'), ('Jelani', 'first', 'male', 'african'),
-- Greek
('Nikolaos', 'first', 'male', 'greek'), ('Dimitri', 'first', 'male', 'greek'),
('Alexandros', 'first', 'male', 'greek'), ('Stavros', 'first', 'male', 'greek'),
-- Slavic
('Ivan', 'first', 'male', 'slavic'), ('Nikolai', 'first', 'male', 'slavic'),
('Dmitri', 'first', 'male', 'slavic'), ('Sergei', 'first', 'male', 'slavic'),
('Alexei', 'first', 'male', 'slavic'), ('Viktor', 'first', 'male', 'slavic')
ON CONFLICT (name, name_type, gender, cultural_origin) DO NOTHING;

-- First Names - Female
INSERT INTO public.character_names (name, name_type, gender, cultural_origin) VALUES
-- English/American
('Elizabeth', 'first', 'female', 'english'), ('Victoria', 'first', 'female', 'english'),
('Catherine', 'first', 'female', 'english'), ('Margaret', 'first', 'female', 'english'),
('Charlotte', 'first', 'female', 'english'), ('Emma', 'first', 'female', 'english'),
('Olivia', 'first', 'female', 'english'), ('Sophia', 'first', 'female', 'english'),
('Isabella', 'first', 'female', 'english'), ('Grace', 'first', 'female', 'english'),
('Eleanor', 'first', 'female', 'english'), ('Alice', 'first', 'female', 'english'),
('Caroline', 'first', 'female', 'english'), ('Amelia', 'first', 'female', 'english'),
('Hannah', 'first', 'female', 'english'), ('Sarah', 'first', 'female', 'english'),
('Rachel', 'first', 'female', 'english'), ('Rebecca', 'first', 'female', 'english'),
('Emily', 'first', 'female', 'english'), ('Abigail', 'first', 'female', 'english'),
-- Irish
('Siobhan', 'first', 'female', 'irish'), ('Aoife', 'first', 'female', 'irish'),
('Niamh', 'first', 'female', 'irish'), ('Ciara', 'first', 'female', 'irish'),
('Saoirse', 'first', 'female', 'irish'), ('Maeve', 'first', 'female', 'irish'),
-- Spanish
('Maria', 'first', 'female', 'spanish'), ('Sofia', 'first', 'female', 'spanish'),
('Carmen', 'first', 'female', 'spanish'), ('Isabel', 'first', 'female', 'spanish'),
('Lucia', 'first', 'female', 'spanish'), ('Elena', 'first', 'female', 'spanish'),
('Rosa', 'first', 'female', 'spanish'), ('Valentina', 'first', 'female', 'spanish'),
-- Italian
('Giulia', 'first', 'female', 'italian'), ('Francesca', 'first', 'female', 'italian'),
('Alessandra', 'first', 'female', 'italian'), ('Chiara', 'first', 'female', 'italian'),
('Bianca', 'first', 'female', 'italian'), ('Lucia', 'first', 'female', 'italian'),
-- French
('Marie', 'first', 'female', 'french'), ('Claire', 'first', 'female', 'french'),
('Isabelle', 'first', 'female', 'french'), ('Marguerite', 'first', 'female', 'french'),
('Amelie', 'first', 'female', 'french'), ('Colette', 'first', 'female', 'french'),
-- German
('Anna', 'first', 'female', 'german'), ('Greta', 'first', 'female', 'german'),
('Liesel', 'first', 'female', 'german'), ('Ingrid', 'first', 'female', 'german'),
('Heidi', 'first', 'female', 'german'), ('Frieda', 'first', 'female', 'german'),
-- Scandinavian
('Freya', 'first', 'female', 'scandinavian'), ('Astrid', 'first', 'female', 'scandinavian'),
('Sigrid', 'first', 'female', 'scandinavian'), ('Ingrid', 'first', 'female', 'scandinavian'),
('Helga', 'first', 'female', 'scandinavian'), ('Liv', 'first', 'female', 'scandinavian'),
-- Japanese
('Yuki', 'first', 'female', 'japanese'), ('Sakura', 'first', 'female', 'japanese'),
('Hana', 'first', 'female', 'japanese'), ('Akiko', 'first', 'female', 'japanese'),
('Keiko', 'first', 'female', 'japanese'), ('Mei', 'first', 'female', 'japanese'),
-- Chinese
('Mei', 'first', 'female', 'chinese'), ('Lin', 'first', 'female', 'chinese'),
('Xiu', 'first', 'female', 'chinese'), ('Hua', 'first', 'female', 'chinese'),
('Yan', 'first', 'female', 'chinese'), ('Jing', 'first', 'female', 'chinese'),
-- Indian
('Priya', 'first', 'female', 'indian'), ('Ananya', 'first', 'female', 'indian'),
('Lakshmi', 'first', 'female', 'indian'), ('Devi', 'first', 'female', 'indian'),
('Meera', 'first', 'female', 'indian'), ('Kavya', 'first', 'female', 'indian'),
-- Arabic
('Fatima', 'first', 'female', 'arabic'), ('Aisha', 'first', 'female', 'arabic'),
('Layla', 'first', 'female', 'arabic'), ('Nadia', 'first', 'female', 'arabic'),
('Yasmin', 'first', 'female', 'arabic'), ('Samira', 'first', 'female', 'arabic'),
-- African
('Amara', 'first', 'female', 'african'), ('Zuri', 'first', 'female', 'african'),
('Nia', 'first', 'female', 'african'), ('Imani', 'first', 'female', 'african'),
('Ayana', 'first', 'female', 'african'), ('Kaya', 'first', 'female', 'african'),
-- Greek
('Helena', 'first', 'female', 'greek'), ('Athena', 'first', 'female', 'greek'),
('Sophia', 'first', 'female', 'greek'), ('Irene', 'first', 'female', 'greek'),
-- Slavic
('Natasha', 'first', 'female', 'slavic'), ('Katarina', 'first', 'female', 'slavic'),
('Anastasia', 'first', 'female', 'slavic'), ('Tatiana', 'first', 'female', 'slavic'),
('Olga', 'first', 'female', 'slavic'), ('Irina', 'first', 'female', 'slavic')
ON CONFLICT (name, name_type, gender, cultural_origin) DO NOTHING;

-- Last Names (neutral gender)
INSERT INTO public.character_names (name, name_type, gender, cultural_origin) VALUES
-- English
('Smith', 'last', 'neutral', 'english'), ('Jones', 'last', 'neutral', 'english'),
('Williams', 'last', 'neutral', 'english'), ('Brown', 'last', 'neutral', 'english'),
('Taylor', 'last', 'neutral', 'english'), ('Davies', 'last', 'neutral', 'english'),
('Wilson', 'last', 'neutral', 'english'), ('Evans', 'last', 'neutral', 'english'),
('Walker', 'last', 'neutral', 'english'), ('Wright', 'last', 'neutral', 'english'),
('Robinson', 'last', 'neutral', 'english'), ('Thompson', 'last', 'neutral', 'english'),
('White', 'last', 'neutral', 'english'), ('Hughes', 'last', 'neutral', 'english'),
('Edwards', 'last', 'neutral', 'english'), ('Green', 'last', 'neutral', 'english'),
('Hall', 'last', 'neutral', 'english'), ('Lewis', 'last', 'neutral', 'english'),
('Harris', 'last', 'neutral', 'english'), ('Clarke', 'last', 'neutral', 'english'),
-- Irish
('Murphy', 'last', 'neutral', 'irish'), ('Kelly', 'last', 'neutral', 'irish'),
('Sullivan', 'last', 'neutral', 'irish'), ('Walsh', 'last', 'neutral', 'irish'),
('OBrien', 'last', 'neutral', 'irish'), ('Byrne', 'last', 'neutral', 'irish'),
('Ryan', 'last', 'neutral', 'irish'), ('OConnor', 'last', 'neutral', 'irish'),
-- Spanish
('Garcia', 'last', 'neutral', 'spanish'), ('Rodriguez', 'last', 'neutral', 'spanish'),
('Martinez', 'last', 'neutral', 'spanish'), ('Lopez', 'last', 'neutral', 'spanish'),
('Hernandez', 'last', 'neutral', 'spanish'), ('Gonzalez', 'last', 'neutral', 'spanish'),
('Perez', 'last', 'neutral', 'spanish'), ('Sanchez', 'last', 'neutral', 'spanish'),
-- Italian
('Rossi', 'last', 'neutral', 'italian'), ('Russo', 'last', 'neutral', 'italian'),
('Ferrari', 'last', 'neutral', 'italian'), ('Esposito', 'last', 'neutral', 'italian'),
('Bianchi', 'last', 'neutral', 'italian'), ('Romano', 'last', 'neutral', 'italian'),
('Colombo', 'last', 'neutral', 'italian'), ('Ricci', 'last', 'neutral', 'italian'),
-- French
('Martin', 'last', 'neutral', 'french'), ('Bernard', 'last', 'neutral', 'french'),
('Dubois', 'last', 'neutral', 'french'), ('Thomas', 'last', 'neutral', 'french'),
('Robert', 'last', 'neutral', 'french'), ('Richard', 'last', 'neutral', 'french'),
('Petit', 'last', 'neutral', 'french'), ('Durand', 'last', 'neutral', 'french'),
-- German
('Mueller', 'last', 'neutral', 'german'), ('Schmidt', 'last', 'neutral', 'german'),
('Schneider', 'last', 'neutral', 'german'), ('Fischer', 'last', 'neutral', 'german'),
('Weber', 'last', 'neutral', 'german'), ('Meyer', 'last', 'neutral', 'german'),
('Wagner', 'last', 'neutral', 'german'), ('Becker', 'last', 'neutral', 'german'),
-- Scandinavian
('Andersen', 'last', 'neutral', 'scandinavian'), ('Johansen', 'last', 'neutral', 'scandinavian'),
('Larsen', 'last', 'neutral', 'scandinavian'), ('Nielsen', 'last', 'neutral', 'scandinavian'),
('Hansen', 'last', 'neutral', 'scandinavian'), ('Pedersen', 'last', 'neutral', 'scandinavian'),
-- Japanese
('Tanaka', 'last', 'neutral', 'japanese'), ('Yamamoto', 'last', 'neutral', 'japanese'),
('Watanabe', 'last', 'neutral', 'japanese'), ('Suzuki', 'last', 'neutral', 'japanese'),
('Takahashi', 'last', 'neutral', 'japanese'), ('Sato', 'last', 'neutral', 'japanese'),
('Kobayashi', 'last', 'neutral', 'japanese'), ('Nakamura', 'last', 'neutral', 'japanese'),
-- Chinese
('Wang', 'last', 'neutral', 'chinese'), ('Li', 'last', 'neutral', 'chinese'),
('Zhang', 'last', 'neutral', 'chinese'), ('Liu', 'last', 'neutral', 'chinese'),
('Chen', 'last', 'neutral', 'chinese'), ('Yang', 'last', 'neutral', 'chinese'),
('Huang', 'last', 'neutral', 'chinese'), ('Zhou', 'last', 'neutral', 'chinese'),
-- Indian
('Patel', 'last', 'neutral', 'indian'), ('Sharma', 'last', 'neutral', 'indian'),
('Singh', 'last', 'neutral', 'indian'), ('Kumar', 'last', 'neutral', 'indian'),
('Reddy', 'last', 'neutral', 'indian'), ('Gupta', 'last', 'neutral', 'indian'),
('Kapoor', 'last', 'neutral', 'indian'), ('Malhotra', 'last', 'neutral', 'indian'),
-- Arabic
('Hassan', 'last', 'neutral', 'arabic'), ('Ali', 'last', 'neutral', 'arabic'),
('Khan', 'last', 'neutral', 'arabic'), ('Ahmed', 'last', 'neutral', 'arabic'),
('Mohammed', 'last', 'neutral', 'arabic'), ('Ibrahim', 'last', 'neutral', 'arabic'),
-- African
('Okafor', 'last', 'neutral', 'african'), ('Mensah', 'last', 'neutral', 'african'),
('Nkosi', 'last', 'neutral', 'african'), ('Diallo', 'last', 'neutral', 'african'),
('Adeyemi', 'last', 'neutral', 'african'), ('Kamau', 'last', 'neutral', 'african'),
-- Greek
('Papadopoulos', 'last', 'neutral', 'greek'), ('Stavros', 'last', 'neutral', 'greek'),
('Nikolaidis', 'last', 'neutral', 'greek'), ('Georgiou', 'last', 'neutral', 'greek'),
-- Slavic
('Ivanov', 'last', 'neutral', 'slavic'), ('Petrov', 'last', 'neutral', 'slavic'),
('Volkov', 'last', 'neutral', 'slavic'), ('Kozlov', 'last', 'neutral', 'slavic'),
('Novak', 'last', 'neutral', 'slavic'), ('Kowalski', 'last', 'neutral', 'slavic')
ON CONFLICT (name, name_type, gender, cultural_origin) DO NOTHING;

-- Verify the table was created and populated
SELECT
    name_type,
    gender,
    COUNT(*) as count
FROM public.character_names
GROUP BY name_type, gender
ORDER BY name_type, gender;
