-- Mercado Nativo — cria o banco de dados vazio no MySQL (rode uma vez, antes do primeiro uso).
-- As TABELAS não precisam ser criadas aqui: o backend cria e atualiza sozinho ao iniciar
-- (app/db/migrations.py).
--
-- Como rodar: no phpMyAdmin/MySQL Workbench, cole este texto e execute;
-- ou no terminal:  mysql -u root -p < backend\database\criar_banco.sql

CREATE DATABASE IF NOT EXISTS mercado_nativo
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- Opcional (recomendado fora do computador de desenvolvimento): um usuário só para o sistema,
-- em vez do root. Troque a senha e use-a no DATABASE_URL do backend/.env:
--   DATABASE_URL=mysql+pymysql://mn_user:SUA_SENHA@localhost:3306/mercado_nativo
-- CREATE USER IF NOT EXISTS 'mn_user'@'localhost' IDENTIFIED BY 'SUA_SENHA';
-- GRANT ALL PRIVILEGES ON mercado_nativo.* TO 'mn_user'@'localhost';
-- FLUSH PRIVILEGES;
