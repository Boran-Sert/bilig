-- Ünitesi bulunamayan test sorusunun da yazılabilmesi için sorunun ünitesini isteğe bağlı yapar.
ALTER TABLE question
    ALTER COLUMN curriculum_unit_id DROP NOT NULL;
