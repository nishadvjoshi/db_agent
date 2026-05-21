-- MySQL dump 10.13  Distrib 9.6.0, for macos15.7 (arm64)
--
-- Host: 127.0.0.1    Database: physician_portal
-- ------------------------------------------------------
-- Server version	9.6.0

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
SET @MYSQLDUMP_TEMP_LOG_BIN = @@SESSION.SQL_LOG_BIN;
SET @@SESSION.SQL_LOG_BIN= 0;

--
-- GTID state at the beginning of the backup 
--

SET @@GLOBAL.GTID_PURGED=/*!80000 '+'*/ 'a9a45700-0cf1-11f1-bfec-a546706090b0:1-4301';

--
-- Current Database: `physician_portal`
--

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `physician_portal` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;

USE `physician_portal`;

--
-- Table structure for table `allergies`
--

DROP TABLE IF EXISTS `allergies`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `allergies` (
  `allergy_id` bigint NOT NULL AUTO_INCREMENT,
  `patient_id` bigint NOT NULL,
  `allergen_name` varchar(150) NOT NULL,
  `reaction` varchar(150) DEFAULT NULL,
  `severity` varchar(20) DEFAULT NULL,
  `status` varchar(20) DEFAULT 'ACTIVE',
  `recorded_date` date DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`allergy_id`),
  KEY `idx_allergy_patient` (`patient_id`),
  CONSTRAINT `fk_allergy_patient` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`patient_id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `appointments`
--

DROP TABLE IF EXISTS `appointments`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `appointments` (
  `appointment_id` bigint NOT NULL AUTO_INCREMENT,
  `patient_id` bigint NOT NULL,
  `physician_id` bigint NOT NULL,
  `appointment_datetime` datetime NOT NULL,
  `status` varchar(30) NOT NULL DEFAULT 'SCHEDULED',
  `reason` varchar(255) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`appointment_id`),
  KEY `idx_appt_patient_dt` (`patient_id`,`appointment_datetime`),
  KEY `idx_appt_phys_dt` (`physician_id`,`appointment_datetime`),
  CONSTRAINT `fk_appt_patient` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`patient_id`),
  CONSTRAINT `fk_appt_physician` FOREIGN KEY (`physician_id`) REFERENCES `physicians` (`physician_id`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `caremap_steps`
--

DROP TABLE IF EXISTS `caremap_steps`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `caremap_steps` (
  `caremap_step_id` bigint NOT NULL AUTO_INCREMENT,
  `caremap_id` bigint NOT NULL,
  `step_number` int NOT NULL,
  `step_name` varchar(200) NOT NULL,
  `due_date` date DEFAULT NULL,
  `completed_date` date DEFAULT NULL,
  `status` varchar(30) NOT NULL DEFAULT 'PENDING',
  `notes` varchar(500) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`caremap_step_id`),
  UNIQUE KEY `uq_caremap_step` (`caremap_id`,`step_number`),
  KEY `idx_step_caremap` (`caremap_id`),
  CONSTRAINT `fk_step_caremap` FOREIGN KEY (`caremap_id`) REFERENCES `caremaps` (`caremap_id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `caremaps`
--

DROP TABLE IF EXISTS `caremaps`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `caremaps` (
  `caremap_id` bigint NOT NULL AUTO_INCREMENT,
  `patient_id` bigint NOT NULL,
  `primary_icd9_code` varchar(10) DEFAULT NULL,
  `title` varchar(200) NOT NULL,
  `status` varchar(30) NOT NULL DEFAULT 'ACTIVE',
  `start_date` date DEFAULT NULL,
  `end_date` date DEFAULT NULL,
  `steps_json` json DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`caremap_id`),
  KEY `idx_caremap_patient` (`patient_id`),
  KEY `idx_caremap_icd9` (`primary_icd9_code`),
  CONSTRAINT `fk_caremap_icd9` FOREIGN KEY (`primary_icd9_code`) REFERENCES `icd9_codes` (`icd9_code`),
  CONSTRAINT `fk_caremap_patient` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`patient_id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `icd9_codes`
--

DROP TABLE IF EXISTS `icd9_codes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `icd9_codes` (
  `icd9_code` varchar(10) NOT NULL,
  `description` varchar(255) NOT NULL,
  PRIMARY KEY (`icd9_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `patients`
--

DROP TABLE IF EXISTS `patients`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `patients` (
  `patient_id` bigint NOT NULL AUTO_INCREMENT,
  `member_number` varchar(50) DEFAULT NULL,
  `first_name` varchar(100) NOT NULL,
  `last_name` varchar(100) NOT NULL,
  `dob` date DEFAULT NULL,
  `gender` varchar(20) DEFAULT NULL,
  `phone` varchar(30) DEFAULT NULL,
  `email` varchar(200) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`patient_id`),
  UNIQUE KEY `member_number` (`member_number`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `physicians`
--

DROP TABLE IF EXISTS `physicians`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `physicians` (
  `physician_id` bigint NOT NULL AUTO_INCREMENT,
  `npi` varchar(20) DEFAULT NULL,
  `first_name` varchar(100) NOT NULL,
  `last_name` varchar(100) NOT NULL,
  `specialty` varchar(100) DEFAULT NULL,
  `phone` varchar(30) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`physician_id`),
  UNIQUE KEY `npi` (`npi`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Current Database: `ai_agent_catalog`
--

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `ai_agent_catalog` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;

USE `ai_agent_catalog`;

--
-- Table structure for table `catalog_columns`
--

DROP TABLE IF EXISTS `catalog_columns`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `catalog_columns` (
  `run_id` varchar(64) NOT NULL,
  `schema_name` varchar(64) NOT NULL,
  `table_name` varchar(64) NOT NULL,
  `column_name` varchar(64) NOT NULL,
  `data_type` varchar(64) DEFAULT NULL,
  `is_nullable` varchar(64) DEFAULT NULL,
  `column_key` varchar(64) DEFAULT NULL,
  `extra` varchar(64) DEFAULT NULL,
  `column_default` text,
  `ai_description` text,
  `ai_generated_by` varchar(64) DEFAULT NULL,
  `ai_generated_at` varchar(64) DEFAULT NULL,
  PRIMARY KEY (`run_id`,`schema_name`,`table_name`,`column_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `catalog_docs`
--

DROP TABLE IF EXISTS `catalog_docs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `catalog_docs` (
  `doc_id` varchar(64) NOT NULL,
  `run_id` varchar(64) DEFAULT NULL,
  `doc_type` varchar(64) DEFAULT NULL,
  `payload_json` text,
  `created_at` varchar(64) DEFAULT NULL,
  PRIMARY KEY (`doc_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `catalog_foreign_keys`
--

DROP TABLE IF EXISTS `catalog_foreign_keys`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `catalog_foreign_keys` (
  `run_id` varchar(64) NOT NULL,
  `schema_name` varchar(64) NOT NULL,
  `table_name` varchar(64) NOT NULL,
  `column_name` varchar(64) NOT NULL,
  `ref_schema_name` varchar(64) NOT NULL,
  `ref_table_name` varchar(64) NOT NULL,
  `ref_column_name` varchar(64) NOT NULL,
  `constraint_name` varchar(64) DEFAULT NULL,
  PRIMARY KEY (`run_id`,`schema_name`,`table_name`,`column_name`,`ref_schema_name`,`ref_table_name`,`ref_column_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `catalog_learned_concepts`
--

DROP TABLE IF EXISTS `catalog_learned_concepts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `catalog_learned_concepts` (
  `concept_name` varchar(64) NOT NULL,
  `description` text,
  `synonyms_json` text,
  `table_hints_json` text,
  `column_hints_json` text,
  `learned_at` varchar(64) DEFAULT NULL,
  PRIMARY KEY (`concept_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `catalog_profiles`
--

DROP TABLE IF EXISTS `catalog_profiles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `catalog_profiles` (
  `run_id` varchar(64) NOT NULL,
  `schema_name` varchar(64) NOT NULL,
  `table_name` varchar(64) NOT NULL,
  `column_name` varchar(64) NOT NULL,
  `inferred_semantic_type` varchar(64) DEFAULT NULL,
  `sample_values_json` text,
  `notes` text,
  PRIMARY KEY (`run_id`,`schema_name`,`table_name`,`column_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `catalog_runs`
--

DROP TABLE IF EXISTS `catalog_runs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `catalog_runs` (
  `run_id` varchar(255) NOT NULL,
  `created_at` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`run_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `catalog_schemas`
--

DROP TABLE IF EXISTS `catalog_schemas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `catalog_schemas` (
  `run_id` varchar(64) NOT NULL,
  `schema_name` varchar(64) NOT NULL,
  PRIMARY KEY (`run_id`,`schema_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `catalog_tables`
--

DROP TABLE IF EXISTS `catalog_tables`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `catalog_tables` (
  `run_id` varchar(64) NOT NULL,
  `schema_name` varchar(64) NOT NULL,
  `table_name` varchar(64) NOT NULL,
  `row_count` bigint DEFAULT NULL,
  `ai_description` text,
  `ai_generated_by` varchar(64) DEFAULT NULL,
  `ai_generated_at` varchar(64) DEFAULT NULL,
  PRIMARY KEY (`run_id`,`schema_name`,`table_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
SET @@SESSION.SQL_LOG_BIN = @MYSQLDUMP_TEMP_LOG_BIN;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-05-21 10:30:24
