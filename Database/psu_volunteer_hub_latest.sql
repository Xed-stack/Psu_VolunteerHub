-- MariaDB dump 10.19  Distrib 10.4.32-MariaDB, for Win64 (AMD64)
--
-- Host: localhost    Database: psu_volunteer_hub
-- ------------------------------------------------------
-- Server version	10.4.32-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `activity_categories`
--

DROP TABLE IF EXISTS `activity_categories`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `activity_categories` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=17 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `activity_categories`
--

LOCK TABLES `activity_categories` WRITE;
/*!40000 ALTER TABLE `activity_categories` DISABLE KEYS */;
INSERT INTO `activity_categories` VALUES (14,'Arts & Culture'),(4,'Community'),(11,'Community Development'),(12,'Disaster Response'),(5,'Education'),(9,'Education & Literacy'),(3,'Environment'),(1,'General'),(6,'Health'),(10,'Health & Wellness'),(15,'Sports & Recreation'),(2,'Technology'),(13,'Technology & Digital');
/*!40000 ALTER TABLE `activity_categories` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `analytics_summaries`
--

DROP TABLE IF EXISTS `analytics_summaries`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `analytics_summaries` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `campus_id` int(11) DEFAULT NULL,
  `metric_type` varchar(100) NOT NULL,
  `value` float NOT NULL,
  `period` varchar(50) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `campus_id` (`campus_id`),
  CONSTRAINT `analytics_summaries_ibfk_1` FOREIGN KEY (`campus_id`) REFERENCES `campuses` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `analytics_summaries`
--

LOCK TABLES `analytics_summaries` WRITE;
/*!40000 ALTER TABLE `analytics_summaries` DISABLE KEYS */;
/*!40000 ALTER TABLE `analytics_summaries` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `attendance`
--

DROP TABLE IF EXISTS `attendance`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `attendance` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `registration_id` int(11) NOT NULL,
  `user_id` int(11) DEFAULT NULL,
  `event_id` int(11) NOT NULL,
  `status` enum('present','absent','excused') DEFAULT NULL,
  `hours_completed` float DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `registration_id` (`registration_id`),
  KEY `user_id` (`user_id`),
  KEY `event_id` (`event_id`),
  CONSTRAINT `attendance_ibfk_1` FOREIGN KEY (`registration_id`) REFERENCES `registrations` (`id`) ON DELETE CASCADE,
  CONSTRAINT `attendance_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `attendance_ibfk_3` FOREIGN KEY (`event_id`) REFERENCES `events` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `attendance`
--

LOCK TABLES `attendance` WRITE;
/*!40000 ALTER TABLE `attendance` DISABLE KEYS */;
/*!40000 ALTER TABLE `attendance` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `campuses`
--

DROP TABLE IF EXISTS `campuses`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `campuses` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `code` varchar(20) NOT NULL,
  `description` text DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `code` (`code`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `campuses`
--

LOCK TABLES `campuses` WRITE;
/*!40000 ALTER TABLE `campuses` DISABLE KEYS */;
INSERT INTO `campuses` VALUES (1,'Lingayen','LINGAYEN',''),(2,'Urdaneta','URDANETA',''),(3,'Asingan','ASINGAN',''),(4,'Bayambang','BAYAMBANG',''),(5,'Binmaley','BINMALEY',''),(6,'Infanta','INFANTA',''),(7,'San Carlos','SANCARLOS',''),(8,'Santa Maria','STAMARIA',''),(9,'Alaminos','ALAMINOS','');
/*!40000 ALTER TABLE `campuses` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `event_announcements`
--

DROP TABLE IF EXISTS `event_announcements`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `event_announcements` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `event_id` int(11) NOT NULL,
  `author_id` int(11) DEFAULT NULL,
  `announcement_type` enum('last_call','event_update','cancelled_postponed') NOT NULL,
  `message` text NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `author_id` (`author_id`),
  KEY `ix_event_announcements_event_id` (`event_id`),
  CONSTRAINT `event_announcements_ibfk_1` FOREIGN KEY (`event_id`) REFERENCES `events` (`id`) ON DELETE CASCADE,
  CONSTRAINT `event_announcements_ibfk_2` FOREIGN KEY (`author_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `event_announcements`
--

LOCK TABLES `event_announcements` WRITE;
/*!40000 ALTER TABLE `event_announcements` DISABLE KEYS */;
/*!40000 ALTER TABLE `event_announcements` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `event_skills`
--

DROP TABLE IF EXISTS `event_skills`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `event_skills` (
  `event_id` int(11) NOT NULL,
  `skill_id` int(11) NOT NULL,
  PRIMARY KEY (`event_id`,`skill_id`),
  KEY `skill_id` (`skill_id`),
  CONSTRAINT `event_skills_ibfk_1` FOREIGN KEY (`event_id`) REFERENCES `events` (`id`) ON DELETE CASCADE,
  CONSTRAINT `event_skills_ibfk_2` FOREIGN KEY (`skill_id`) REFERENCES `skills` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `event_skills`
--

LOCK TABLES `event_skills` WRITE;
/*!40000 ALTER TABLE `event_skills` DISABLE KEYS */;
INSERT INTO `event_skills` VALUES (1,13),(1,14),(1,15),(1,16),(2,9),(2,17),(2,18),(3,15),(3,19),(3,20),(4,13),(4,15),(4,21),(4,22),(5,10),(5,23),(5,24),(5,25),(6,13),(6,15),(6,22),(6,26),(6,27),(7,9),(7,20),(7,25),(8,15),(8,19),(8,23),(8,24),(9,9),(9,13),(9,17);
/*!40000 ALTER TABLE `event_skills` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `events`
--

DROP TABLE IF EXISTS `events`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `events` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `title` varchar(200) NOT NULL,
  `description` text NOT NULL,
  `date` datetime NOT NULL,
  `end_date` datetime DEFAULT NULL,
  `cancellation_deadline` datetime DEFAULT NULL,
  `category` varchar(50) DEFAULT NULL,
  `location` varchar(500) DEFAULT NULL,
  `slots` int(11) DEFAULT NULL,
  `cover_image_path` varchar(255) DEFAULT NULL,
  `cover_image_name` varchar(255) DEFAULT NULL,
  `cover_uploaded_by_id` int(11) DEFAULT NULL,
  `cover_uploaded_at` datetime DEFAULT NULL,
  `campus_id` int(11) DEFAULT NULL,
  `created_by_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `campus_id` (`campus_id`),
  KEY `fk_events_created_by` (`created_by_id`),
  KEY `fk_events_cover_uploaded_by` (`cover_uploaded_by_id`),
  CONSTRAINT `events_ibfk_1` FOREIGN KEY (`campus_id`) REFERENCES `campuses` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_events_cover_uploaded_by` FOREIGN KEY (`cover_uploaded_by_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_events_created_by` FOREIGN KEY (`created_by_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `events`
--

LOCK TABLES `events` WRITE;
/*!40000 ALTER TABLE `events` DISABLE KEYS */;
INSERT INTO `events` VALUES (1,'Youth Coding Mentor','Help Grade 6 students at San Carlos Central School learn basic Python and logic.','2026-09-06 21:04:20',NULL,NULL,'Technology','',20,NULL,NULL,NULL,NULL,1,NULL),(2,'Green Campus Initiative','Participate in our monthly tree planting and sustainable landscaping project.','2026-09-13 21:04:20',NULL,NULL,'Environment','',50,NULL,NULL,NULL,NULL,1,NULL),(3,'Community Food Drive','Help organize and distribute relief packages to affected local barangays.','2026-09-09 21:04:20',NULL,NULL,'Community','',30,NULL,NULL,NULL,NULL,2,NULL),(4,'Rural Literacy Program','Teach foundational reading and mathematics to children in remote communities.','2026-09-01 00:00:00',NULL,NULL,'Education','',15,'uploads/events/93b839c4290040bea9b36b5a2abc86ab.jpg','download_2.jpg',NULL,NULL,1,NULL),(5,'Disaster Response Training','Participate in basic first aid and disaster preparedness workshop.','2026-09-04 21:04:20',NULL,NULL,'Health','',40,NULL,NULL,NULL,NULL,3,NULL),(6,'Community IT Support Workshop','Help bridge the digital divide by teaching elderly residents how to use modern tools.','2026-09-29 21:04:20',NULL,NULL,'Technology','',25,NULL,NULL,NULL,NULL,4,NULL),(7,'Coastal Cleanup Drive','Monthly environmental drive to preserve the Lingayen coastline.','2026-09-02 21:04:20',NULL,NULL,'Environment','',100,NULL,NULL,NULL,NULL,1,NULL),(8,'Community Wellness Fair','Assist medical personnel in organizing a free health mission.','2026-10-14 21:04:20',NULL,NULL,'Health','',60,NULL,NULL,NULL,NULL,7,NULL),(9,'Sustainable Farming Demo','Learn about organic cultivation and irrigation management.','2026-10-29 21:04:20',NULL,NULL,'Environment','',30,NULL,NULL,NULL,NULL,8,NULL);
/*!40000 ALTER TABLE `events` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `external_participants`
--

DROP TABLE IF EXISTS `external_participants`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `external_participants` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `id_number` varchar(50) NOT NULL,
  `name` varchar(100) DEFAULT NULL,
  `contact_number` varchar(50) DEFAULT NULL,
  `address` text DEFAULT NULL,
  `email` varchar(120) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `id_number` (`id_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `external_participants`
--

LOCK TABLES `external_participants` WRITE;
/*!40000 ALTER TABLE `external_participants` DISABLE KEYS */;
/*!40000 ALTER TABLE `external_participants` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `historical_activities`
--

DROP TABLE IF EXISTS `historical_activities`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `historical_activities` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `source_key` varchar(64) NOT NULL,
  `source_document` varchar(255) NOT NULL,
  `source_page` int(11) NOT NULL,
  `source_row` int(11) NOT NULL,
  `unit_name` varchar(120) NOT NULL,
  `campus_id` int(11) DEFAULT NULL,
  `title` varchar(500) NOT NULL,
  `activity_type` varchar(30) DEFAULT NULL,
  `partners` text DEFAULT NULL,
  `participant_categories` text DEFAULT NULL,
  `volunteer_count` int(11) DEFAULT NULL,
  `year_conducted` int(11) DEFAULT NULL,
  `imported_at` datetime NOT NULL,
  `imported_by_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_historical_activities_source_key` (`source_key`),
  KEY `campus_id` (`campus_id`),
  KEY `ix_historical_activities_year_conducted` (`year_conducted`),
  KEY `ix_historical_activities_unit_name` (`unit_name`),
  KEY `fk_historical_imported_by` (`imported_by_id`),
  CONSTRAINT `fk_historical_imported_by` FOREIGN KEY (`imported_by_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
  CONSTRAINT `historical_activities_ibfk_1` FOREIGN KEY (`campus_id`) REFERENCES `campuses` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=432 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `historical_activities`
--

LOCK TABLES `historical_activities` WRITE;
/*!40000 ALTER TABLE `historical_activities` DISABLE KEYS */;
INSERT INTO `historical_activities` VALUES (216,'8f7a8152e7afd56de6ae37a4fd7de9db817a0ab6c15cb7ff85f0df290721c446','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',3,1,'Alaminos Campus',9,'Project TUBAYON Sabay-sa Pag Ahon','Outreach','PSU ALAMINOS, PSU Systems Teachi ng and Non- Teaching Staff','Teachers, SSC Students',55,2020,'2026-08-30 13:11:14',NULL),(217,'1f35f837d54e26afc8f56ec9fc53961b4a1e730710dbd963815fcd9e84c02082','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',3,2,'Alaminos Campus',9,'Community Pantry in Adopted Barang of PSU Alaminos City','Outreach','PSU Alaminos Facult y , Bolaney and Bisocol Barangay Council','Teachers, Barangay Council',20,2021,'2026-08-30 13:11:14',NULL),(218,'97d82d11c9f5e9b3cd868ab36b5ac698d569e3908793cd9bc2201d58ea6c8df6','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',3,3,'Alaminos Campus',9,'Technological Application Seminar to Barangay Bolaney and Bisoccol,Alaminos City, Pangasinan','Extension','PSU Alaminos Facult y , Bolaney and Bisocol Barangay Council','Teacher, Barangay Council, Parents',30,2021,'2026-08-30 13:11:14',NULL),(219,'ef94cf77feea2ff247cad16d1a8cf4ebbf9a7e7ecd472dde033e19566b70d8fd','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',3,4,'Alaminos Campus',9,'World Environmental Day -REI- refreshing World thru Planting , Environmental Pr otection and Coastal Clean Up','Extension /Outreach','PSU Alaminos , Faculty & Non- Teaching Staff, SSC ,Students, Vice Mayor of Alaminos City Ho. Ion Fontelera, Hon. Apple Joy Bacay, Hon. Raul Bacay, Alaminos City Nation High School Batch \'80, Ms. Angelique Aquino, Miss Iya De Vera, JCI Hundred Islands, the Fraternal Order of Eagles Hundred Islands Chapter, Bolaney Council','Teachers, Non- Teaching Staff, Students, Vice Mayor Ion Fontelera, Barangay Officials of Bolaney, AEGLES, JCI, Hon. Apple Joy Bacay- Tolentino, Hon . Raul Bacay, Alaminos City National High School Batch \'80. Miss Angelique Ancheta, Miss Iya De Vera',700,2024,'2026-08-30 13:11:14',NULL),(220,'2ed497f53cb8a6079d60cafceab40483ef97b8bf5457f220369ebd8ba9df67cb','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',4,5,'Alaminos Campus',9,'Liwawa : Giving Light and Hope to the Community','Outreach','PSU Alaminos Facult y , Pangapisan, and Poblacion, Barangay Council','Teachers, Non- Teaching Staff, Students, Barangay Officials of Pangapisan, Poblacion, Cayucay,KALIP I Selected Members',50,2024,'2026-08-30 13:11:14',NULL),(221,'57f978b7dab5e5714a503244f8ccae4cb77753963ca4c89ee6a00317be5a6e96','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',4,6,'Alaminos Campus',9,'Repacking of Goods LGU Alaminos City','Outreach','PSU Alaminos Faculty, LGU Alaminos, Selected PSU University Officials','Teachers, Non- Teaching Staff, Students, Selected Officials of PSU',150,2025,'2026-08-30 13:11:14',NULL),(222,'065ff5d4f46ddaa5c31a0fa75740ae0f5ab011ae5ca9e510bcb801334a17653a','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',4,7,'Alaminos Campus',9,'PSU System Donation for Typhoon Emong','Outreach','PSU SYSTEM , LGU ALAMINOS CITY, DSWD, Barangay Council of San Roque,','PSU President, VP Presidents, Directors, Teachers, Non- Teaching Staff, Departm ent Heads of LGU, Human Resources Officers',35,2025,'2026-08-30 13:11:14',NULL),(223,'644c2107d25f18dd25c7daef7e1d738b7ca91304030d9cda31974b4135657150','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',4,8,'Alaminos Campus',9,'Adopt-A-Family Project Isasakatuparan','Extension','PSU SYSTEM , LGU ALAMINOS CITY, DSWD, Barangay Council of San Roque,','PSU Engineering Dept. , Extension Coordinator, PRPIO, Brgy. Councilor',10,2025,'2026-08-30 13:11:14',NULL),(224,'d2a48109e3d7a14a697249a1e2ac512a63117d05186e12a1dad71cda0f0f6ce9','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',5,9,'Alaminos Campus',9,'Alaminos City Extension Coordinator Emp owers Youth at an International UN/UNESCO event','Outreach','PSU ALAMINOS CIT Y, INTERNATIONA L COUNCIL IN EDUCATION RESEARCH & TRAINING','Professors, Teachers, Students, Environmentali sts, Economists, School Administrators',298,2025,'2026-08-30 13:11:14',NULL),(225,'c9e4d5925ccb8deb1a530ac1ca461ab4f15496814d3275840bb4c0e363c849a4','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',5,1,'Asingan Campus',3,'Little Learners, Big Stories: Pedagogy Plus Nurtures Love for Reading (Phase 1)','Extension','Cabuloan Elementary School','Faculty and staff of PSU- AC, elementary teachers and pupils of Cabuloan Elementary School',35,2021,'2026-08-30 13:11:14',NULL),(226,'ccb0f6e3454f5e7aa3f16682248f5e1d82609d6d4d2798329142e79cf306bfdc','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',5,2,'Asingan Campus',3,'Phase 1: Mastery of the Fundamental Mathematical Operations Using Math Player Game App (Mathinik App)','Extension','San Vicente West Integrated School','Faculty and staff of PSU- AC, elementary Math teachers and grade 3 pupils',45,2021,'2026-08-30 13:11:14',NULL),(227,'04a71cc7672dc83db8ed3755f01614e92a2594264b67c83b1f47f7e5e0a03ec9','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',5,3,'Asingan Campus',3,'Pedagogy Plus Extension Program (Phase 2)','Extension','Cabuloan Elementary School','Faculty and staff of PSU- AC, elementary teachers and pupils of Cabuloan Elementary School',35,2022,'2026-08-30 13:11:14',NULL),(228,'7b1fa1a5cc149f02623d3de959e41fa44b1b3deb19aeccaba59b246f093be689','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',5,4,'Asingan Campus',3,'Phase 2: Mastery of the Fundamental Mathematical Operations Using Math Player Game App (Mathinik App)','Extension','San Vicente West Integrated School','Faculty and staff of PSU- AC, elementary Math teachers and grade 3 pupils',40,2022,'2026-08-30 13:11:14',NULL),(229,'72c819361951204dd78f3b55600e610677d146412ce1742d96c765891ad22d45','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',6,5,'Asingan Campus',3,'PCSMT and EEG Launch PedagogyPLUS with Cabuloan Elementary School (Phase 3)','Extension','PCSMT and Cabuloan Elementary School','Faculty and staff of PSU- AC, elementary teachers and pupils of Cabuloan Elementary School',40,2023,'2026-08-30 13:11:14',NULL),(230,'c683d0d91c389cc2e2427a6b7dd1555a1d3257e4d2ae2e235cdd91fb469792bf','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',6,6,'Asingan Campus',3,'PSU-AC empowers Bolinao housewives with sustainable livelihood','Extension','LGU of Asingan','Faculty and staff of PSU-AC and Bolinao housewives',36,2023,'2026-08-30 13:11:14',NULL),(231,'b6ea352adf5d37218310cc6544f9f509249494286cbcae915d63f65e36020856','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',6,7,'Asingan Campus',3,'Innovative ‘3- Wheeled Classroom\' for OSYs launched at PSU-AC','Extension','LGU of Asingan/DepEd','Out-of-school youth, faculty and staff of PSU-AC',45,2023,'2026-08-30 13:11:14',NULL),(232,'10c40f8f92cc6a38b9936b1642eebd2ef6b9b0c34c0e2f70fa74857dfcdc84f6','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',6,8,'Asingan Campus',3,'PSU-AC Students Share the Gift of Life Through Blood Donation','Outreach','PSU-AC NSTP- ROTC','PSU Asingan Campus NSTP- ROTC students',126,2024,'2026-08-30 13:11:14',NULL),(233,'29879e9dec18dbd6defb93454ab2f2eba040f31d80c4c711d482b08b417f6540','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',6,9,'Asingan Campus',3,'Phase 3: Mastery of the Fundamental Mathematical Operations Using Math Player Game App (Mathinik App)','Extension','San Vicente West Integrated School','Faculty and staff of PSU- AC, elementary Math teachers and grade 3 pupils',30,2024,'2026-08-30 13:11:14',NULL),(234,'6d13fe73c7dbacc4d0ef9cfdb9af18d8d436124fd86699d9378c65a5b78bbc38','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',6,10,'Asingan Campus',3,'Phase 4: Mastery of the Fundamental Mathematical Operations Using Math Player Game App (Mathinik App)','Extension','San Vicente West Integrated School','Faculty and staff of PSU- AC, elementary Math teachers and grade 3 pupils',32,2025,'2026-08-30 13:11:14',NULL),(235,'207efc7117246a19a38b97c1765841ec7dbd04f60a8a5a85fd887c73c7fc713e','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',6,11,'Asingan Campus',3,'Project ECO: Students Lead the Green Move in Domanpot','Outreach','PSU Asingan Campus','Faculty, Staff and Students',96,2025,'2026-08-30 13:11:14',NULL),(236,'677cf5e7927f03eccb21a6fc29cfbb5d7fd7cab10a34dd3a058857150f01df4b','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',7,12,'Asingan Campus',3,'PSU-AC Leads Free Training to Equip Students, Educators, and Communities','Extension','PSU Asingan Campus','Senior high school students, job seekers, out-of- school youth, educators, and local residents',43,2025,'2026-08-30 13:11:14',NULL),(237,'d75f3beec1e5e89bb88febe2b4bd0aad59b51f9fc1036a9409eef49b450ec6bb','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',7,1,'Bayambang Campus',4,'PSU Bayambang Community Pantry','Outreach','LGU Bayambang','Teachers, Non- Teaching Staff and Students',500,2021,'2026-08-30 13:11:14',NULL),(238,'9ce49d6fddedd4e3ac50e798f3faf8709d4985e587d3ba611db81e90908d00d5','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',7,2,'Bayambang Campus',4,'Computer Literacy Training for Tanolong Elementary School Teachers: A Training Workshop for using Office 365, Google Docs, Virtual Meeting Application, Open Source LMS, And Internet Etiquette','Extension','DepEd- Tanolong Elementary School','Teachers',10,2021,'2026-08-30 13:11:14',NULL),(239,'9a8839dadc58f2eb81c3d1abfba46ac14a9d5cc48ba52914d9c717eb2592f276','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',7,3,'Bayambang Campus',4,'Training on Sweet Treats Processing','Extension','DOST/ City of Alaminos','Teachers',3,2021,'2026-08-30 13:11:14',NULL),(240,'05b22551f085470133277b25a2e0764baa7260a1b8f99f77d568434887f52d72','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',7,4,'Bayambang Campus',4,'PROJECT CARE: Collaborative Assistance for Resilient Education','Extension','DepEd- Tanolong Elementary School','Teachers and Students',20,2021,'2026-08-30 13:11:14',NULL),(241,'5d501019c51cc1c8a920b92be2af39cca86c2bda8f0715ad4ae1a51fe9d0ba0d','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',7,5,'Bayambang Campus',4,'LiTEACHracy Link Project-Year 4','Extension','Tanolong Day Care Workers','Teachers, Students and Non-teaching staff',12,2021,'2026-08-30 13:11:14',NULL),(242,'2fddb1b6c46f4de64315d41eaf99446804174ee592614cebf1b22caf9e5998c2','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',7,6,'Bayambang Campus',4,'Bani Elementary School Computer Literacy Training Program','Extension','DepEd- Bani Elementary School','Teachers',10,2021,'2026-08-30 13:11:14',NULL),(243,'63933904f537a89b40e35e0d082199e6b07ac646b89dfab21b82b63264a62d78','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',8,7,'Bayambang Campus',4,'LIS Valentines Gift Giving 2023','Outreach','Bani Elementary School','Teachers and Students',20,2023,'2026-08-30 13:11:14',NULL),(244,'9a9d5346631f101056119a66f1d29a43cfc9e39e11e01161d95ddcd78bed4b97','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',8,8,'Bayambang Campus',4,'Linang Plus( Tech-Book)','Extension','DepEd- Bani Elementary School and Tanolong Elementary School','Teachers and Students',34,2023,'2026-08-30 13:11:14',NULL),(245,'4565071484476de446cc19bf917199b726ac0e785641416ae1b5e512b79ce602','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',8,9,'Bayambang Campus',4,'LINANG 1: Information Dissemination of GAD Messages and Concepts and GCED LINANG 4: IM Ready','Extension','Barangay Bani and DepEd Bani Elementary School','Teachers and Students',20,2023,'2026-08-30 13:11:14',NULL),(246,'0c4227af46b9289efd812f11d0d102e190a03389c132de7d0bac51e596ebeb80','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',8,10,'Bayambang Campus',4,'Workshop on Action Research','Extension','DepEd Tanolong Elementary School and Bani Elementary School','Teachers',15,2023,'2026-08-30 13:11:14',NULL),(247,'4dde2f60b50d96550fe984080ca497b3fc1230145352373bdab423477d6a6496','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',8,11,'Bayambang Campus',4,'Project CARE: Collaborative Assistance for Resilient Education at Tanolong Elementary School','Extension','DepEd Tanolong Elementary School and Bani Elementary School','Teachers and Students',15,2023,'2026-08-30 13:11:14',NULL),(248,'178fbf1d0f0d4d0dc2baf5b14b767126a4ec1d42cd70dcbe2413256812e3301e','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',8,12,'Bayambang Campus',4,'Gift Giving BEEgenerous: A Gift of Love for the Children of Our Community','Outreach','DepEd Tanolong Elementary School and Bani Elementary School','Teachers and Students',30,2023,'2026-08-30 13:11:14',NULL),(249,'306b8f1b16dcd5b792e935db00d76e1713b3f2dd7f10de1c702596cd45aaa74d','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',8,13,'Bayambang Campus',4,'Together for Better Language Teaching','Extension','DepEd Bautista NHS and Cipriano P. Primicias NHS','Teachers',10,2023,'2026-08-30 13:11:14',NULL),(250,'df62c6826231e69b69c11baa1da4ac71cd1bd09ef957f491efc1d0f0ce009a7f','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',9,14,'Bayambang Campus',4,'Research UndaGo','Extension','Department of Education','Teachers',10,2023,'2026-08-30 13:11:14',NULL),(251,'5fb8fe5910c38dd1d9efdbda35caf09c7898af51107acfc81e0037f217088d80','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',9,15,'Bayambang Campus',4,'ExPRESS\' Writing Workshop on Campus Journalism','Extension','Department of Education','Teachers',10,2023,'2026-08-30 13:11:14',NULL),(252,'96c68546be1840fcd6276803168d756963c621e3ae682f70f58b09aaa0ef3b78','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',9,16,'Bayambang Campus',4,'Project LIFE: Learning the Importance of Family through Education','Extension','DepEd- Tanolong National High School','Teachers',10,2023,'2026-08-30 13:11:14',NULL),(253,'ed184c3dfac66cfb852995d64cdfa4b4fabdd27ff939c1d61ff2f6470f222ff1','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',9,17,'Bayambang Campus',4,'Project HEALTH (Health, Education Action and Livelihood for a Happy Life); Project Herbal Gardening','Extension','DepEd- Tanolong National High School','Teachers and Students',15,2023,'2026-08-30 13:11:14',NULL),(254,'47bc6e49a11728bc2d10961c647f7cb25b9959e92a9e9d9464f6900b1cea2174','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',9,18,'Bayambang Campus',4,'\"Isulong Kalusugan Project\" under Program Health (Health, Education Action and Livelihood for a Happy Life)','Extension','DepEd- Tanolong National High School','Teachers and Students',30,2023,'2026-08-30 13:11:14',NULL),(255,'a6d5fb94d8e15b5f6eef82ce2640612271024edf2d4ce8d53e2115c5a7e83a16','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',9,19,'Bayambang Campus',4,'PROJECT READ (Reaching to Enhance the Skills of Students with Reading Difficulties)','Extension','DepEd- Tanolong National High School','Teachers and Students',20,2023,'2026-08-30 13:11:14',NULL),(256,'2cc86c5598dd1279ba87a49a479778268bd178e1f09187d40cd63feb768d84fe','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',9,20,'Bayambang Campus',4,'Project SMART: Science and Mathematics Assistance, Review and Tutorial','Extension','DepEd- Tanolong National High School','Teachers and Students',25,2023,'2026-08-30 13:11:14',NULL),(257,'c1e2503633382f498fb5f791d039923228f83ea317c9c08e214b54c0c7e165f0','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',9,21,'Bayambang Campus',4,'BSBA Livelihood Training Program In Barangay Bani, Bayambang, Pangasinan','Extension','Barangay Bani, Bayambang','Teachers',10,2023,'2026-08-30 13:11:14',NULL),(258,'528be150d97d4b14f6eaaf0ef739327a3bb1053d5f7a6623e9efbe5e4815a0d4','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',10,22,'Bayambang Campus',4,'Ituro ko, Isasayaw Mo','Extension','Bani Elementary School','Teachers and Students',10,2023,'2026-08-30 13:11:14',NULL),(259,'c0c5adfcbd54a23ab619b7e0ca5543091c4657c93ad9b3d382b8118ce0a5496e','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',10,23,'Bayambang Campus',4,'Computer Literacy Training for Bani Elementary School Teachers Phase 3: A Training Workshop for Advance topic in Microsoft Excel Formulas and the Use of Graphs and Charts for Data Visualization','Extension','Bani Elementary School','Teachers',10,2023,'2026-08-30 13:11:14',NULL),(260,'ad52a6ef91f00c236730837ae29d6a88c24f5b04dfbda50722cb1dcb742053be','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',10,24,'Bayambang Campus',4,'FROM THE HEART: SPREADING LOVE AND CARE An Outreach Program of the Science and Mathematics Department','Outreach','DepEd- Tanolong National High School','Teachers and Students',22,2024,'2026-08-30 13:11:14',NULL),(261,'78fd4e3ad82e34685a611631b5f5bbbad5f3bf642d6d16f426407fa4f69a5ffb','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',10,25,'Bayambang Campus',4,'Give Love on Valentine\'s Day Outreach Program','Outreach','Missionaries of Charity','Teachers',5,2024,'2026-08-30 13:11:14',NULL),(262,'65aa9517e64246997457db04613c81ca4c2118ef6b9bb36f006d1c35bdb4058f','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',10,26,'Bayambang Campus',4,'Computer Literacy Training for Tanolong Elemen tary School Teachers Phase 4: Microsoft Office 365 Productivity','Extension','Tanolong Elementary School','Teachers',10,2024,'2026-08-30 13:11:14',NULL),(263,'adca5ff8b3f82a7c841aaee0701c1f5ffbd18cc3efdacf3eaadf7283b190d66e','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',10,27,'Bayambang Campus',4,'Gift Giving “Giving is All About Love” and Feeding Program Activity 2024 at Obillo Elementary School, Barangay Pantol Bayambang Pangasinan.','Outreach','Obillo Elementary School','Teachers and Students',20,2024,'2026-08-30 13:11:14',NULL),(264,'8d6575bc74ed83b765dfcf231ae71ecb45aa932e6cf1d2a1846908d89faccc98','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',11,28,'Bayambang Campus',4,'Eat Well, Live Well','Outreach','Bayambang District Hospital','Teachers and Students',16,2024,'2026-08-30 13:11:14',NULL),(265,'7a4695c219464741fc0ee0db5ad15a1100b460dd6dc4c89fb41aea667d499d0f','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',11,29,'Bayambang Campus',4,'Brigada Eskwela 2024: MathSci-ya para sa Malinis at Ligtas na Umpisa','Outreach','DepEd- Tanolong National High School','Teachers and Students',10,2024,'2026-08-30 13:11:14',NULL),(266,'854354a79b8c91cd6beb3fd98395510bd5ca3efb5e571f401a105e8c842ad2ad','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',11,30,'Bayambang Campus',4,'Brigada Eskwela 2024: PROJECT ITSO CLEAN','Outreach','DepEd- Tanolong Elementary School','Teachers and Students',13,2024,'2026-08-30 13:11:14',NULL),(267,'a45476d51c34eebeabdedd7c9a08efebcd3a16677275b70819e364044fd277d8','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',11,31,'Bayambang Campus',4,'BTLED\'s Nutritional Care for Tanolong Students','Outreach','DepEd- Tanolong Elementary School','Teachers and Students',10,2024,'2026-08-30 13:11:14',NULL),(268,'5521fb5732838ccca63a95d111b2bc10a6c6c33fbbee44b98e7fd52e0a36cb91','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',11,32,'Bayambang Campus',4,'\"Trash-Formation: Turning Waste to Opportunity for a Sustainable Community\"','Outreach','Barangay Bani, Bayambang','Teachers and Students',20,2024,'2026-08-30 13:11:14',NULL),(269,'3f715e9cdfc9e5434f9ea7a31bb606e2f7e6a3e5672d7b165d37b820ee5ad19b','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',11,33,'Bayambang Campus',4,'Tiny Steps; Big Dreams – Inspiring Health, Learning and Fun in Buenlag Elementary School','Outreach','Buenlag Elementary School','Teachers and Students',17,2024,'2026-08-30 13:11:14',NULL),(270,'4c1c89130b9606c22af343d05e1ab87712e992614d13cf5c5a4af7bb7f682e9d','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',11,34,'Bayambang Campus',4,'SALIWAY: Saya at Liwanag Ating Yakap 2024','Outreach','Tanolong National High School','Teachers and Students',68,2024,'2026-08-30 13:11:14',NULL),(271,'1276915f79fc506ec9589f2c246ed871e0297bf0e7a61fa253f7cdcb36d17a0b','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',11,35,'Bayambang Campus',4,'Bachelor of Public Administration Gift Giving Outreach Program','Outreach','Barangay San Pedro Ili, Alcala','Teachers and Students',15,2024,'2026-08-30 13:11:14',NULL),(272,'5fe0ccaae64c59983a3e90687f572221f922956dd258106d52d4e8181a81300c','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',11,36,'Bayambang Campus',4,'Project: REGALOVE','Outreach','Cason Elementary School','Teachers and Students',37,2024,'2026-08-30 13:11:14',NULL),(273,'8cdbb965374d5c3054dd10f180f6c22d13d8f6f1bd9f7a6d66172bcf738e2a1e','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',12,37,'Bayambang Campus',4,'S.T.E.P. Forward: Sharing True Empathy and Presents with Children and Senior Citizens','Outreach','Buenlag Elementary School','Teachers and Students',45,2024,'2026-08-30 13:11:14',NULL),(274,'0823ccf3fd84590dd0c2f89e527d88d047a3b568e174b6f3af211f58c43a8285','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',12,38,'Bayambang Campus',4,'KALINGANG LD: Pamaskong Handog 2024','Outreach','Tanolong National High School','Teachers and Students',48,2024,'2026-08-30 13:11:14',NULL),(275,'d500d51e9371238de3ed3892a2b98fe074deff42722bb5ad951abeb557e8dc97','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',12,39,'Bayambang Campus',4,'Health Caravan','Outreach','Red Cross- San Carlos Chapter','Teachers and Students',642,2024,'2026-08-30 13:11:14',NULL),(276,'7888bcd4a5e27c3839b40ddc5a53fe89556de889b74a8124bd232c7c0d7b42c4','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',12,40,'Bayambang Campus',4,'Gift Giving and Outreach Program at Obillo Elementary School','Outreach','Obillo Elementary School','Teachers and Students',15,2024,'2026-08-30 13:11:14',NULL),(277,'5ed0c30d8a2b77077a857d75e715577375699c57c87b8b3cdcee509235cf8a0e','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',12,41,'Bayambang Campus',4,'BSBA GIFT- GIVING ACTIVITY 2024','Outreach','Barangay Bani, Bayambang','Teachers and Students',15,2024,'2026-08-30 13:11:14',NULL),(278,'9621cd0de6c5f537f0f33bcfe73139afbce0f8a03ab98bf9f1acc7204a3c0417','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',12,42,'Bayambang Campus',4,'PSU BAYAMBANG CAMPUS BSBA STUDENTS UNITE FOR TYPHOON VICTIMS IN NUEVA ECIJA','Outreach','LGU Nueva Ecija','Teachers and Students',20,2024,'2026-08-30 13:11:14',NULL),(279,'181da19fa246c44f65f42c7f4d5d2f785b649a637ab6b07be31cd028180723ce','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',12,43,'Bayambang Campus',4,'Mobile Blood Donation Drive','Outreach','Red Cross- San Carlos Chapter','Teachers and Students',36,2024,'2026-08-30 13:11:14',NULL),(280,'b26fa4f649f52d19aca102931dd4e58e98f09ec26865c0b6ae3db80f8323e94e','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',12,44,'Bayambang Campus',4,'Development of a Computerized Management System for A. Diaz Sr. Elementary School','Extension','DepEd A. Diaz Sr. Elementary School','Teachers and Students',10,2024,'2026-08-30 13:11:14',NULL),(281,'f5c18421f163927a47d4e8677a3a93a162de33d4566e196ad194ecf7ebbf6f43','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',12,45,'Bayambang Campus',4,'REPRODUCTIVE HEALTH AWARENESS AND INTERVENTION PROGRAM AMONG TEENAGE PARENTS IN BRGY BANI, BAYAMBANG, PANGASINAN (2nd phase)','Extension','Barangay Bani, Bayambang','Teachers',10,2024,'2026-08-30 13:11:14',NULL),(282,'90391c0c3805e0961531b7155132ec9d01159e206a846e47eb69f4ec20015bf6','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',13,46,'Bayambang Campus',4,'Barangay Innovative Strategies and Knowledge-Based Engagement for Good Governance Phase 1. Rapping the Gavel: SK Empowerment','Extension','SK Bayambang','Teachers',17,2024,'2026-08-30 13:11:14',NULL),(283,'5f440f16cb0a2d1d0ba5722fae558e30ef47af4cd7c3e8cf0190e18a6796c676','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',13,47,'Bayambang Campus',4,'Project SMART (Science and Mathematics Assistance, Review and Tutorial)','Extension','Tanolong National High School','Teachers and Students',15,2024,'2026-08-30 13:11:14',NULL),(284,'023e835e4372e223cff4e378edf54bf974272b9540d006895712cb486110520c','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',13,48,'Bayambang Campus',4,'Project READ (Reaching Out to Enhance the Skills and Abilities of Students with Reading Difficulties)','Extension','Tanolong National High School','Teachers and Students',15,2024,'2026-08-30 13:11:14',NULL),(285,'65c84071b50a5569f66be273625e84ff121c5c4544dda1d105a1fafa97f78b27','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',13,49,'Bayambang Campus',4,'Project Life: “Learning the Importance of Family Through Education”','Extension','Tanolong National High School','Teachers and Students',15,2024,'2026-08-30 13:11:14',NULL),(286,'9091e6c33a678eb0cc095403006e05cd42fb46d56e644e1a908d20216c24630e','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',13,50,'Bayambang Campus',4,'Effective Business Correspondence: Elevating Writing and Communication to a Professional Level','Extension','Bani Elementary School','Teachers and Students',15,2024,'2026-08-30 13:11:14',NULL),(287,'5a5077fea48863d5b20fbc6e6e91b6765be687675a2bd4ecbeed184bfdf33819','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',14,51,'Bayambang Campus',4,'Computer Literacy Training for Bani Elementary School Teachers Phase 3: A Training Workshop Interactive Instructional Materials and Microsoft Office 365 Productivity','Extension','Bani Elementary School','Teachers and Students',15,2024,'2026-08-30 13:11:14',NULL),(288,'13117ead8cc583de36df49bf593ce277c962a32fdcbbcd3cc654b556ffdadfe7','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',14,52,'Bayambang Campus',4,'Project LINANG (Literasiya para kay Nanay at Inang) PLUS','Extension','Bani Elementary School','Teachers and Students',15,2024,'2026-08-30 13:11:14',NULL),(289,'3597f8e7bba57fb648ffbd9c077c42f73e70e8222e87387285ca4ca48e8b49fe','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',14,53,'Bayambang Campus',4,'Project SMART (Science and Mathematics Assistance, Review and Tutorial)','Extension','Tanolong National High School','Teachers and Students',22,2025,'2026-08-30 13:11:14',NULL),(290,'9650c48aabfbff45c204bff72966b9fde42a9bd43377dd6ce395e6ebf37582c8','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',14,54,'Bayambang Campus',4,'Project LINGAP: Global Citizenship Education Module and GAD-related IEC Materials for Local Government Units in the Philippines with DRRM','Extension','Bani Elementary School','Teachers and Students',15,2025,'2026-08-30 13:11:14',NULL),(291,'022e7832f748f675091bd53f0b8e234d3398457b9efb0ab1febdf5dba1d46093','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',14,55,'Bayambang Campus',4,'Tutorial Program for Non- Numerates','Extension','Tanolong National High School','Teachers and Students',10,2025,'2026-08-30 13:11:14',NULL),(292,'b622f7fa5384bf20ef1f3d976d2677c2d6896df7bc4e0f7b07cdf9aa78ab711d','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',14,56,'Bayambang Campus',4,'Project LiNANG (Literasiya para kay Nanay at Inang) PLUS Training on Gender and Development','Extension','Bani Elementary School','Teachers and Students',15,2025,'2026-08-30 13:11:14',NULL),(293,'8315cd03dfad9cdbc2b72094bad9cd64afd86fa07723260d50a5627d8d7e9f95','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',15,57,'Bayambang Campus',4,'Livelihood Skills Training Program (Women\'s Month Seminar-Forum) in Barangay Bani, Bayambang, Pangasinan','Extension','Barangay Bani, Bayambang','Teachers and Students',15,2025,'2026-08-30 13:11:14',NULL),(294,'99c48b9b46e914833028210c66547cdbec0341bc856027bfc13840122df84c2b','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',15,58,'Bayambang Campus',4,'Volunteerism for Miss Basista Pre- Pageant and Pageant Night (Technical Assistance)','Outreach','LGU Basista','Teachers and Students',8,2025,'2026-08-30 13:11:14',NULL),(295,'4230ad3c2b3f9e957330a190f583aa598bd80f8d920317d545d6c4fcb4335703','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',15,59,'Bayambang Campus',4,'ACTIVITY: “TOASTIES AND TOGETHERNES S” Outreach','Outreach','Bani Elementary School','Teachers and Students',15,2025,'2026-08-30 13:11:14',NULL),(296,'04bf756347d0017d10c2d108a3606988ffc5e85b010f8843f60d5ba383560b76','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',15,1,'Binmaley Campus',5,'Feed Formulation and Feeding Management Training for Aquaculture Activities in Pangasinan','Extension','PSU Binmaley Campus and Barangay Canaoalan, Binmaley, Pangasinan','PSU Binmaley Campus faculty, staff and students',15,2022,'2026-08-30 13:11:14',NULL),(297,'8fe7f2e285e76c52498e3866d1ec4036827300184312cc5a8f15beda9e38a801','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',15,2,'Binmaley Campus',5,'livelihood training program in the adopted barangay','Extension','PSU Binmaley Campus GAD unit and Barangay Buenlag, Binmaley, Pangasinan','PSU Binmaley Campus faculty, staff and students',10,2022,'2026-08-30 13:11:14',NULL),(298,'300be51e44c514847f382da8601e90e5d43891db4fd066c2f4894d8a36439503','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',15,3,'Binmaley Campus',5,'Training on Fish Processing','Extension','DOST 1','PSU Binmaley Campus faculty, staff and students',10,2022,'2026-08-30 13:11:14',NULL),(299,'fdb4c8ae0b7c88b82e423f259d1197cd20179f9c7ecc9ba22ef9176bceb0f565','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',16,4,'Binmaley Campus',5,'Training on Bangus Longganisa Making','Extension','PSU Binmaley Campus and Barangay Caloocan Norte, Binmaley, Pangasinan','PSU Binmaley Campus faculty, staff and students',20,2023,'2026-08-30 13:11:14',NULL),(300,'784606b65f50fabda2d2b54927e257f702414382b92560f165732fc4c10611c5','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',16,5,'Binmaley Campus',5,'Training on Fish Processing and Bangus Longganisa Making','Extension','Our Lady of Purification Parish Binmaley','PSU Binmaley Campus faculty, staff and students',20,2023,'2026-08-30 13:11:14',NULL),(301,'f594f859eef077323001c5718b52ddea7ca475f5477721b002f5e38e6bf36d2e','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',16,6,'Binmaley Campus',5,'High Five for First semester 2023- 2024','Outreach','PSU Binmaley Campus and SSC Officers','PSU Binmaley Campus faculty, staff and students',200,2023,'2026-08-30 13:11:14',NULL),(302,'5e2d38b4cf236f42545853aa428948de636338df498da568a03d52301005ad7a','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',16,7,'Binmaley Campus',5,'Adopt-a-Book Program Phase 1','Outreach','PSU Binmaley Campus','PSU Binmaley Campus students',100,2024,'2026-08-30 13:11:14',NULL),(303,'763d6b3261fbea30344da6a145ec144b8d08e13939a95c335a8e0ea8c2279f76','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',16,8,'Binmaley Campus',5,'Adopt-a-Book Program Phase 2','Outreach','PSU Binmaley Campus and Barangay Palma, Basista, Pangasinan','PSU Binmaley Campus students',NULL,2024,'2026-08-30 13:11:14',NULL),(304,'6384888df4353f571733457345b14976c363e92750f528bd729021bc9367c361','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',16,9,'Binmaley Campus',5,'Blood Donation Drive','Outreach','PSU BC and R1- Medical Center','PSU Binmaley Campus faculty, staff and students',134,2024,'2026-08-30 13:11:14',NULL),(305,'ca4467e84d0329a9621c98d6dd2727251452a9569ee6be39f8ca62657b4b0299','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',16,10,'Binmaley Campus',5,'Fire Safety Drill','Extension','PSU BC and BFP Lingayen','Criminology students and ROTC students',100,2024,'2026-08-30 13:11:14',NULL),(306,'d4670170408253cccf0dcbd65d19ca97f0961d4a71c778612de50b535f5f5578','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',16,11,'Binmaley Campus',5,'Campus Brigada 2024','Extension','PSU - BC, BFP, LGU San Isidro Norte, Binmalely PNP','PSU Binmaley Campus faculty, staff and students',200,2024,'2026-08-30 13:11:14',NULL),(307,'efc52fa4ea891de4de3ee5a4c8d60e3c1883a278d97f5f9947a1d83db0283567','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',16,12,'Binmaley Campus',5,'Comprehensive Food Safety in Fish Processing','Extension','Barangay San Isidro Norte','PSU Binmaley Campus faculty, staff and students',10,2024,'2026-08-30 13:11:14',NULL),(308,'0b5be05fe5cbb26aa74427be253a344c045626c07a1c23945288bf8d6710ca65','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',16,13,'Binmaley Campus',5,'\"Raising Awareness in the Biology of Geloina expanse among Local Bivalve Gleaners in Lingayen, Pangasinan','Extension','Barangay Bantayan and Fisheries Science Department of PSU Binmaley Campus','PSU Binmaley Campus faculty, staff and students',30,2024,'2026-08-30 13:11:14',NULL),(309,'f18900bc40222fb998dd6f3d09d43a69caaeed2b01d7747f1038496f07903eac','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',17,14,'Binmaley Campus',5,'Blood Donation Drive','Outreach','Region 1 Medical Center','Faculty, Staff and Students',96,2025,'2026-08-30 13:11:14',NULL),(310,'0fd8cc828358658a53a508e92eeddaaef20bfb8903523019f287be905a8d2c7c','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',17,15,'Binmaley Campus',5,'Coastal Cleanup Drive','Outreach','PSU - OVPREI; 104th Community Defense Center (CDC) and ROTC Students','Faculty and Non-Teaching',10,2025,'2026-08-30 13:11:14',NULL),(311,'586934595c6f6c91d286175fe11d4fe9a1f17c8da3e2ba7ee9c63d2556469ded','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',17,16,'Binmaley Campus',5,'Brigada Universidad','Extension','PSU Binmaley Campus and SSC Officers','Faculty, Staff and Students',200,2025,'2026-08-30 13:11:14',NULL),(312,'45b1f3a92ebc4d2f2574b42a22c9fe9601cc5980b16b971795526918e4a1568d','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',17,17,'Binmaley Campus',5,'Concreting of the Student Study and Refreshment Area which are low- lying area of the campus which frequently experiences flooding','Outreach','NSTP-UNITE Organization','NSTP Students',100,2025,'2026-08-30 13:11:14',NULL),(313,'12be11688580f41d5ba62c4a6678ae58c4a1742c6460ffc39cb265186c294006','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',17,18,'Binmaley Campus',5,'tYPHOON Donation Drive','Outreach','LGU Alaminos and PSU- OVPREI','LGU Alaminos',10,2025,'2026-08-30 13:11:14',NULL),(314,'8ff2c44cf717b2ebc8e61117b26766cf4d7480758ea5ace6acc97fa66d501201','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',17,19,'Binmaley Campus',5,'Upcycling of wastes to reduce wastes','Outreach','Association of Environmental Science Students for Sustainability and Inclusivity (PSU-AESIN) and DENR-EMB Region 1','Association of Environmental Science Students for Sustainability and Inclusivity (PSU-AESIN)',100,2025,'2026-08-30 13:11:14',NULL),(315,'bb02f0708c88b3fef2ceee13277a2106cf74fe439ca04854183f440dc282e484','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',17,20,'Binmaley Campus',5,'Fire Safety Drills and Awareness','Extension','Bureau of Fire Protection (BFP) Binmaley and PSU-BC','BFP and PSU Faculty, Staff and Students',NULL,2025,'2026-08-30 13:11:14',NULL),(316,'6bfbb06895d4838ce754ccf722c59714764a28470b7b7acc237601db13358863','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',18,1,'Infanta Campus',6,'Research/Extensi on Capsule Writing Workshop & Google Scholar/ORCID/R esearchGate Account Creation','Extension','PSU Infanta Campus faculty, staff, and students','Faculty, staff, students',20,2021,'2026-08-30 13:11:14',NULL),(317,'b341b8724f27c6a5f283df0a3a5755a2617f9b495bce205fd86eea077cf989dc','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',18,2,'Infanta Campus',6,'Webinar: Moringa - Nature\'s Herb to Fight COVID-19 Infection','Extension','PSU Infanta Campus faculty, staff, and students/ Department of Agriculture','Faculty, staff, students',25,2021,'2026-08-30 13:11:14',NULL),(318,'9752817a621bdc8837a46b4791454389a0b3adddb8b547182db5afc34b90e857','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',18,3,'Infanta Campus',6,'Training on Organic Moringa Entrepreneurship','Extension','PSU Infanta Campus faculty, staff, and students / Department of Agriculture','Faculty, staff, students/ farmers',15,2021,'2026-08-30 13:11:14',NULL),(319,'57685e2a9d6d42e25c505b7e6f96f5b7d84cb205a279e17d061ee715cab4872e','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',18,4,'Infanta Campus',6,'Awareness Campaign on Anti-Rabies Act of 2007 and Vaccination Program','Outreach','PSU Infanta Campus faculty, staff, and students / LGU','Faculty, staff, students/fur pa rents',10,2022,'2026-08-30 13:11:14',NULL),(320,'4d127e7aacdacf54cf0f5c9f6a359b5b026cbcd2398649213ef7d9a7fceb51f8','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',18,5,'Infanta Campus',6,'Community Development for IPs in Pangasinan (Phase 1) Livelihood Trainings','Extension','PSU Infanta Campus faculty, staff, and students / LGU','Faculty, staff, students / Infanta Residence',112,2022,'2026-08-30 13:11:14',NULL),(321,'62f61c4313fb61cf79e78c752c002614d75cac6970598e617ce680bc1589c537','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',18,6,'Infanta Campus',6,'Moringa Agriculture Project','Extension','PSU Infanta Campus faculty, staff, and students / Department of Agriculture','Faculty, staff, students/ farmers',25,2023,'2026-08-30 13:11:14',NULL),(322,'018aebdc0cc1a34d639ba07ae0327e709d39f3926abd06029381e6bcd66f5501','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',18,7,'Infanta Campus',6,'Tuturuan Kita','Outreach','PSU Infanta Campus faculty, staff, and students / DepEd','Faculty, staff, students',125,2023,'2026-08-30 13:11:14',NULL),(323,'460534803abca4aea9c1f3640cb037668edae3e25b5ed030e69c712201b2282b','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',19,8,'Infanta Campus',6,'Outreach Program: \"Veganuary Information Awareness Drive- on Vegetarian','Outreach','PSU Infanta Campus faculty, staff, and students / DepEd','Faculty, staff, students',20,2024,'2026-08-30 13:11:14',NULL),(324,'b95609ccfe5bd8ada68cf53cf37e829627ce9635f3ac6e59f5ed6df98e2d4850','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',19,9,'Infanta Campus',6,'Give Love on Valentine\'s Day Outreach Program at Dagupan City Missionaries Charity','Outreach','PSU Infanta Campus faculty, staff, and students','Faculty, staff, students',125,2024,'2026-08-30 13:11:14',NULL),(325,'96516a22b2d682400af2c922fc01aebbf8707bc6027047593eda9c5b00a6cb63','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',19,10,'Infanta Campus',6,'Project BASA (Reading, Arithmetic, Arts, Science, Asal - Values/Araling Panlipunan) sa Barangay Bamban, Infanta, Pangasinan','Outreach','PSU Infanta Campus faculty, staff, and students / DepEd','Faculty, staff, students',140,2024,'2026-08-30 13:11:14',NULL),(326,'3bd56f8d16e9686997bb261ffa1849613d18335a0a5a2041d5259ae8b0e48483','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',19,11,'Infanta Campus',6,'Enriching Education through Instructional and Reading Materials at Bayambang National High School, Infanta, Pangasinan','Outreach','PSU Infanta Campus faculty, staff, and students / DepEd','Faculty, staff, students',86,2024,'2026-08-30 13:11:14',NULL),(327,'b42b3107be49306bdddf0aa1a73830127ffb046639ab4ceb3c22c545f49a06a8','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',19,12,'Infanta Campus',6,'Tutorial, Books Donation, and Feeding Outreach Program at three (3) Day Care Centers in Barangay Bamban, Infanta, Pangasinan','Outreach','PSU Infanta Campus faculty, staff, and students / DepEd','Faculty, staff, students',65,2024,'2026-08-30 13:11:14',NULL),(328,'7a2a62f19ec1c8a6741b247675a7eab5fa4f590bb7b1c493c5219fc571d876d0','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',20,13,'Infanta Campus',6,'World Environment Day \"REI-Freshing the World thru Tree Planting and Environment Clean-up\"','Outreach','PSU Infanta Campus faculty, staff, and students / Department of Agriculture','Faculty, staff, students/farmer s',75,2024,'2026-08-30 13:11:14',NULL),(329,'4df8ad834601f890a80af2178ae44eb88525f6c236450ceacdfa849c5aba0f51','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',20,14,'Infanta Campus',6,'Arbor Day Celebration','Outreach','PSU Infanta Campus faculty, staff, and students / Department of Agriculture','Faculty, staff, students/ farmers',110,2024,'2026-08-30 13:11:14',NULL),(330,'d3cea64d79c358dcbd72933d03071d4083e625854cefcf64abcda5ef98a7ff21','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',20,1,'Lingayen Campus',1,'Donation Drive in order to help the victims of Taal Volcano Eruption with the Federated Student Government and Supreme Student Council Lingayen Campus','Outreach','Pangasinan Baker\'s Club Federal Student Government Supremem Student Council Lingayen Campus','Students',8,2020,'2026-08-30 13:11:14',NULL),(331,'bb73b1541034300694119b08b9617523aa7f70397d15494fbd03525ff8d65a41','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',20,2,'Lingayen Campus',1,'BRIGADA UNIBERSIDAD with JBMA (The Junior Business Managers\' Association)','Outreach','Junior Business Manager\'s Association (JBMA) PSU Lingayen Campus','Students',11,2022,'2026-08-30 13:11:14',NULL),(332,'15b1e630412240c21859b50d9116826b747606a55155e95a4754c7c650a62d64','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',20,3,'Lingayen Campus',1,'LIWAWA\'Y KALANGWERAN: The Context of Our Vote in The 2022 Election','Outreach','PSU-Lingayen Campus Supreme Student Council','Students & Teachers',10,2022,'2026-08-30 13:11:14',NULL),(333,'8f81648dca89b98101677f23eacc76a6d9d20005d82a86ccfe31e7552cf1aaa2','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',20,4,'Lingayen Campus',1,'COLLEGE BRIGADA with JBMA (The Junior Business Managers\' Association)','Outreach','Junior Business Manager\'s Association (JBMA) PSU Lingayen Campus','Students & Teachers',25,2022,'2026-08-30 13:11:14',NULL),(334,'67d6362bbc0f478315a51d1d5f86926192c2e9afdaf09627a7882040868b2fca','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',21,5,'Lingayen Campus',1,'LIKET, an outreach program for the healthcare workers and mothers of the barangay Domalandan Center, Lingayen, Pangasinan','Outreach','Supreme Student Council Accredited student Organizations from the MARAHUYO Students\' Festival 2022 PSU Lingayen Campus','Students & Teachers',52,2022,'2026-08-30 13:11:14',NULL),(335,'89ce20ea21658adbf3d13cb48303eaebd9dff5174f242953a55db3db51ced63e','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',21,6,'Lingayen Campus',1,'MANTANEM: Mangrove Tree Planting Activity','Outreach','Students\' Alliance of Future Biologists (SAFB) The Environmentalist s\' Club (TEC) Pangasinan State University, Lingayen Campus Philippine Consortium for Science, Mathematics, and Technology - Students\' Chapter (PSULC- PCSMT-SC)','Students',25,2022,'2026-08-30 13:11:14',NULL),(336,'706c6838a8ffec51b0a3969d001acd08032733982750b3b7e6196d22dcd1ca03','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',21,7,'Lingayen Campus',1,'BPA Students join 1st Provincial Volunteer Engagement Forum','Outreach','National Volunteer Service Coordinating Agency (PNVSCA) Provincial Government of Pangasinan PSU Lingayen Campus','Students',4,2022,'2026-08-30 13:11:14',NULL),(337,'5271806036c9abe5aa062251ffb9b2e5b6888867f34468f106ecf5ff9754d960','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',22,8,'Lingayen Campus',1,'YPAG-IBIG GIFT GIVING 2022 (Young Public Administration Guild)','Outreach','Young Public Administration Guild Missionaries of Charity in Barangay Lucao, Dagupan City, Pangasinan PSU Lingayen Campus','Students',8,2022,'2026-08-30 13:11:14',NULL),(338,'bf567b087815050f6d94a3d6843f82351b50b0cd44d306f4deff0a10203ce869','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',22,9,'Lingayen Campus',1,'Campus Coastal Clean-up Drive at Lingayen Beach with the theme, \"Kapit-bisig para sa Kalikasan: Itanim, Protektahan, at Pangalagaan ang ating Baybayin\"','Outreach','Philippine Army\'s Civil-Military Operation Unit and Reserve Command and the Provincial Government LGU Lingayen Philippine Coast Guard Bureau of Fire and Protection Philippine National Police PSU Lingayen Campus','Students Teachers Coast Guard Police',125,2023,'2026-08-30 13:11:14',NULL),(339,'79a2ccb5172bae259627ed78a5be50612dff076239bc8d8c378c34a59aeb2487','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',22,10,'Lingayen Campus',1,'BSBA conducts Entrep Assist Phase II','Extension','Junior Business Manager\'s Association (JBMA) Barangay Council of Estanza PSU Lingayen Campus','Students & Teachers',18,2023,'2026-08-30 13:11:14',NULL),(340,'ecc273255962bee727f948103f35b5102f72b5f1083440e7691cd0f289be5ebe','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',22,11,'Lingayen Campus',1,'Junior Business Managers\' Association (JBMA) Conducts Annual Gift-Giving Program','Outreach','Junior Business Managers\' Association (JBMA) PSU Lingayen Campus','Students & Teachers',24,2023,'2026-08-30 13:11:14',NULL),(341,'cfdf62173d96b108f38de53eaf73b61e1068cc0de5f83523d49b90b5da090c7d','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',22,12,'Lingayen Campus',1,'The Student Alliance of Future Biologists (SAFB) conducted an outreach program in the Municipal Social Welfare and Development (MSWD) office of Lingayen','Outreach','Student Alliance of Future Biologists (SAFB) Municipal Social Welfare and Development (MSWD) office of Lingayen PSU Lingayen Campus','Students & Teachers',15,2023,'2026-08-30 13:11:14',NULL),(342,'f8bb9380d04f3b5cee7aed9e6fcd1cea9be4f8ca7ee13b68a9799da11f355ec0','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',23,13,'Lingayen Campus',1,'Brigada Unibersidad (Business Administration students, faculty members, and The Junior Business Managers\' Association officers)','Outreach','Junior Business Manager\'s Association (JBMA) PSU Lingayen Campus','Students & Teachers',11,2024,'2026-08-30 13:11:14',NULL),(343,'7a7aad68586355067992f67d4f41748e76483bfb2ae78b3623e0e90fb24453b6','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',23,14,'Lingayen Campus',1,'Timeless Elegance: Grooming and Wellness for Our Beloved Seniors','Outreach','Libsong East Senior Citezens Association PSU Lingayen Campus','Students Teachers Elderly',21,2024,'2026-08-30 13:11:14',NULL),(344,'70b0070eb7f5f17c221c2d88dff60f18dbd442887bdbb91ab04b9d659f841882','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',23,15,'Lingayen Campus',1,'BIRTHDAY BOUNCE BACK theme \"Bawat Bata ay Ligtas, Malusog, at Masaya\"','Outreach','World Vision Foundation Inc. (WVFI) PSU Lingayen Campus','Students & Teachers',50,2024,'2026-08-30 13:11:14',NULL),(345,'85671a3c68533ebed0e3b922deabd9fc8acdf9bbfc8b157aa19ccf9f29a98577','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',23,16,'Lingayen Campus',1,'PSU LC AND R1MC TEAM UP FOR SUCCE SSFUL BLOOD LETTING PROGRAM','Outreach','Region I Medical Center PSU Lingayen Campus','Students & Teachers',25,2024,'2026-08-30 13:11:14',NULL),(346,'670dc341729136bd4a79c43bcd7497c57a11553f6ca2076a611ff267d5205d29','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',23,17,'Lingayen Campus',1,'REI-freshing the World through Tree Planting and Environmental Clean-up','Outreach','PSU Lingayen Campus Reserve Officers\' Training Corps (ROTC)','Students Teachers Non-teaching personnel',32,2024,'2026-08-30 13:11:14',NULL),(347,'9aa178177d9e2ad3c84c33a2ad47d83b743ad24c97f674d176677ba563c11bed','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',24,18,'Lingayen Campus',1,'Plant Trees today for a Greener Future','Outreach','LGU Bugallon PSU Lingayen Campus','Student Teachers Elderly',15,2024,'2026-08-30 13:11:14',NULL),(348,'b7c9c8ace86f49df15bb93fe0d6cbed1db1a7e173f93c5c9c7cabaf09fe1da97','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',24,19,'Lingayen Campus',1,'US PEACE CORPS FORGES PARTNERSHIP WITH PSU LINGAYEN THROUGH VOLUNTEERISM INITIATIVE','Outreach','Philippine National Volunteer Service Coordinating Agency (PNVSCA) PSU Lingayen Campus','Teachers',12,2024,'2026-08-30 13:11:14',NULL),(349,'752ba3a3024d745c3d79a26dd654fd15c0147846ff803bf2e855571336a67a3a','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',24,20,'Lingayen Campus',1,'JBMA joins Brigada Unibersidad (The Junior Business Managers\' Association)','Outreach','Junior Business Manager\'s Association (JBMA) PSU Lingayen Campus','Students',8,2024,'2026-08-30 13:11:14',NULL),(350,'e2381f5731c579aef9a5c5c5df6ad0bde8065f5cb8a2610a032bd4a280ec5d95','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',24,21,'Lingayen Campus',1,'Regional State Colleges and Universities Athletic Association (RSCUAA) at Mariano Marcos State University, Batac City, llocos Norte','Outreach','The Supreme Council of PSU- LC Students\' Services and Alumni Affairs Future Nutritionist - Dietetics\' Club','Students',15,2025,'2026-08-30 13:11:14',NULL),(351,'bcdb145fa4a0e01ffb709d48314ac3f8e50a27b2133bb06ff303c5d6269b82c5','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',24,22,'Lingayen Campus',1,'Communiversidad Coastal Clean-Up','Outreach','PSU Lingayen Campus Reserve Officers\' Training Corps (ROTC)','Students Teachers Non-teaching personnel',150,2025,'2026-08-30 13:11:14',NULL),(352,'d37a7fffd574c08e381506b84ebf55846e5148c27ef0e42908edcd5c027b515f','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',24,23,'Lingayen Campus',1,'Pangasinan State University - Lingayen Campus conducts Project C.A.R.E. (Community Action and Relief during Emergencies)','Outreach','PSU Lingayen Campus','Students Teachers Non-teaching personnel',152,2025,'2026-08-30 13:11:14',NULL),(353,'57d5408dd234b316b029962274a070b577f7d9e08e44ac1ae07b36dbb78b146a','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',25,1,'San Carlos Campus',7,'Mental health awareness month 2021','Outreach','Roxas, San Carlos City, Pangasinan','Teachers and Students',30,2021,'2026-08-30 13:11:14',NULL),(354,'c304e65884f0f304b8f4f35d064b901f47f995603cfb293d2a9424c2b40b27df','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',25,2,'San Carlos Campus',7,'Three Computer Units from Pangasinan State University – San Carlos City Campus','Outreach','Lilimasan San Carlos City, Pangasinan','Teachers and Students',45,2021,'2026-08-30 13:11:14',NULL),(355,'86370f66317ab6575756e71a77242a318547035d8a16008f05b1f2d74094153b','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',25,3,'San Carlos Campus',7,'Computer Literacy to all Barangay Officials','Extension','Lilimasan San Carlos City, Pangasinan','Teachers and Students',56,2021,'2026-08-30 13:11:14',NULL),(356,'44c82e7b4e23f105817b7fc6f0937e5ac0e7a1976e9e678195caea879338dc6f','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',25,4,'San Carlos Campus',7,'Online Learning Modality: The Parents and Guardians Role','Extension','Lilimasan San Carlos City, Pangasinan','Teachers and Students',25,2022,'2026-08-30 13:11:14',NULL),(357,'950a7c016bc602af15eda0055088dad0912d13edc29bca5582eb9612a79b3b52','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',25,5,'San Carlos Campus',7,'Technical Writing (Memoranda, Resolution, and Project Management)','Extension','Lilimasan San Carlos City, Pangasinan','Teachers and Students',25,2022,'2026-08-30 13:11:14',NULL),(358,'3661e9cd7bba6471fb2e0191416ad4031444219f168ff3f5253ab787f6bf5a65','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',25,6,'San Carlos Campus',7,'Edukalidad: Alay Para sa Badjao','Extension','Burgos-Padlan, and Bugallon- Posadas, San Carlos City, Pangasinan','Teachers and Students',40,2023,'2026-08-30 13:11:14',NULL),(359,'a2c05492871b18c98abd3afd519871d7175dab319432ad9f6abc191f6320c5c3','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',25,7,'San Carlos Campus',7,'Outreach Program Pamaskong Handog 2023','Outreach','Burgos-Padlan, and Bugallon- Posadas, San Carlos City, Pangasinan','Students',20,2023,'2026-08-30 13:11:14',NULL),(360,'ed11e0701a835a8508599336928a5b60f538aaf8a9e1e79552323244f2b86394','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',25,8,'San Carlos Campus',7,'Agew na Pasasalamat cum Sharing of Blessings: Alay Biyaya Para Sa Mga Badjao','Outreach','Burgos-Padlan, and Bugallon- Posadas, San Carlos City, Pangasinan','Teachers and Students',50,2023,'2026-08-30 13:11:14',NULL),(361,'a9771462c88b1ed68f006ee92e7339d589dd134c2b746a3c3b10313fc9721aff','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',26,9,'San Carlos Campus',7,'Pamaskong Handog para sa Badjao Community','Outreach','Burgos-Padlan, and Bugallon- Posadas, San Carlos City, Pangasinan','Teachers and Students',45,2023,'2026-08-30 13:11:14',NULL),(362,'b9c500897478ffc0c56e3ee3ed33bb1697355a5acee3d5915c7dede7054091d8','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',26,10,'San Carlos Campus',7,'Exploring Identity: Advancing Perssonal Growth and Development of the Sea Gypsies in San Carlos City, Pangasinan','Extension','Burgos-Padlan, and Bufallon- Posadas, San Carlos City, Pangasinan','Teachers and Students',30,2024,'2026-08-30 13:11:14',NULL),(363,'4e9fcb88b250358f92d29331f1229685d2697f19d54cc84f1ab2b4662c3894cb','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',26,11,'San Carlos Campus',7,'Oplan Ikaw Muna: Phase 1 - How to Flourish Financially \"Finding Your Way to long-term Financial Well- being','Extension','Bogaoan Elementary School and Mabalbalino Elementary School','Teachers and Students',25,2024,'2026-08-30 13:11:14',NULL),(364,'6b594958c79f2c11f7a3433d94d2389a0db657e5be2947dfa23a4003bd9ee64d','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',26,12,'San Carlos Campus',7,'Oplan Ikaw Muna: Phase 1 - Finding your way around financial world \"Knowing the Environment for Financial Service','Extension','Bogaoan Elementary School and Mabalbalino Elementary School','Teachers and Students',25,2024,'2026-08-30 13:11:14',NULL),(365,'fdaafd82841b36dd91a39cb4e606e7b669f4873787b611885cec5178863f6cd4','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',26,13,'San Carlos Campus',7,'Computer Literacy: Basic, Intermediate and Proficient in Elementary School of Payapa and Naguilayan Phase 2','Extension','Payapa and Naguilayan Elementary School','Teachers and Students',29,2024,'2026-08-30 13:11:14',NULL),(366,'546820da4e39b3cd8aba5157e0e39e5503cf7fbee9067d0de4c94f1f77365260','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',26,14,'San Carlos Campus',7,'Culinary Horizons: Empowering Communities through Bottling Process of Bangus Sardines, Gourmet Tuyo, and Pickled Smoked Salmon','Extension','Roxas, San Carlos City, Pangasinan','Teachers and Students',50,2024,'2026-08-30 13:11:14',NULL),(367,'a66622ecd8f1cb7c7a5866beedc9075414c3a24128f717b7f435e1768a781630','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',27,15,'San Carlos Campus',7,'BASIC READING LITERACY AND LITERARY APPRECIATION FOR BADJAO','Extension','Burgos-Padlan, and Bugallon- Posadas, San Carlos City, Pangasinan','Teachers and Students',50,2024,'2026-08-30 13:11:14',NULL),(368,'edcac025f9bb7c40029f9ba8fb4bdb98172e9c9e2672f6a97233a9f2231e71b6','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',27,16,'San Carlos Campus',7,'Outreach Program and Seminar on VAWC for the Sea Gypsies in San Carlos, Pangasinan','Outreach','Burgos-Padlan, and Bugallon- Posadas, San Carlos City, Pangasinan','Teachers and Students',25,2024,'2026-08-30 13:11:14',NULL),(369,'e580c982ce91cd7a0a10481c1b8635ea451506719b7b0d32adb947cf22fb22f9','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',27,17,'San Carlos Campus',7,'LIVELIHOOD SKILLS AND ENTREPRENEU RSHIP TRAINING ON FRUIT VEGETABLE YEAST BREAD PRODUCTS','Extension','Roxas, San Carlos City, Pangasinan','Teachers and Students',50,2024,'2026-08-30 13:11:14',NULL),(370,'dcf985422db7fa32219f37328dbf5c0cfa0967ac4926fb76bc8fed44a0383f78','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',27,18,'San Carlos Campus',7,'Outreach Program and Seminar on VAWC for the Senior Citizens at Lilimasan, San Carlos, Pangasinan','Outreach','Lilimasan, San Carlos, Pangasinan','Teachers and Students',25,2024,'2026-08-30 13:11:14',NULL),(371,'3a82cb5ee099900c8150465e12ee309e2d509e51f38675ead86b8e1516055702','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',27,19,'San Carlos Campus',7,'Pangasinan State University Communiversidad Outreach Activity for Missionaries of Charity','Outreach','Missionaries of Charity','Teachers and Students',15,2024,'2026-08-30 13:11:14',NULL),(372,'25bdc1aeba1184a9db5acae887d37536b035b8176f928c5e8982c87c5264393b','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',27,20,'San Carlos Campus',7,'PSU SC Unites Community in Tree Planting for a Sustainable Future','Outreach','Roxas, San Carlos City, Pangasinan','Teachers and Students',35,2024,'2026-08-30 13:11:14',NULL),(373,'b3f01c8824638239f30197d7c22285fb2c496eb2c2fecc3eb229f434c8075edc','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',27,21,'San Carlos Campus',7,'Sea Gypsy Community Profiling and Outreach Program','Outreach','Burgos-Padlan, and Bugallon- Posadas, San Carlos City, Pangasinan','Teachers and Students',50,2024,'2026-08-30 13:11:14',NULL),(374,'162321bdf0236898267d1a0150b8339f57e4085236144a515257be9f8b867013','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',28,22,'San Carlos Campus',7,'Bayaniyugan sa Bayan ng San Carlos City','Outreach','San Carlos City, Pangasinan','Teachers and Students',100,2024,'2026-08-30 13:11:14',NULL),(375,'57b333c8a9f0793bb732b257eed06e18c6ac42e0a7e118ba05317173cbad10de','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',28,23,'San Carlos Campus',7,'VAWC and TATAK Boluntir Fun Run','Outreach','Lingayen, Pangasinan','Teachers and Students',20,2024,'2026-08-30 13:11:14',NULL),(376,'51d048e133210cc7f2955abd18a4c10d91a0815125ecdb55ca8e0320a3960293','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',28,24,'San Carlos Campus',7,'Alay Biyaya para sa mga Badjao 2024',NULL,'Burgos-Padlan, and Bufallon- Posadas, San Carlos City, Pangasinan','Teachers and Students',NULL,2024,'2026-08-30 13:11:14',NULL),(377,'515e5afcec016c475d2c734e326fc9e24a1f5fae901e8fefdfb9856156a6d28b','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',28,25,'San Carlos Campus',7,'Liwawa: Giving Light and Hope to the Community – a PSU Christmas Special','Outreach','Roxas, San Carlos City, Pangasinan','Students',25,2024,'2026-08-30 13:11:14',NULL),(378,'acc48a337ff6dbc110b234362be81a470c243fc0b5e2ae267b12fd51e549c90a','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',28,26,'San Carlos Campus',7,'Project A+ VERTICAL Gardening: A Positive, Vibrant, Eco-friendly, Resource- efficient, Tech- driven, Innovative, Community- based, Agri- sustainable & Local Gardening','Extension','Lilimasan, San Carlos, Pangasinan','Teachers and Students',50,2025,'2026-08-30 13:11:14',NULL),(379,'2bbd76a610d1c7e2331f27102da494969c93b185eebabeefe28ef8dfec6c6ca4','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',28,27,'San Carlos Campus',7,'Adopt-a-Barangay Project: Gender Responsive Community Engagement and Development','Extension','Lilimasan, San Carlos, Pangasinan','Teachers and Students',50,2025,'2026-08-30 13:11:14',NULL),(380,'be6470c27605f72bc7619b60c08828295b5f89f4d8f8e9770c97041955ab77ae','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',28,28,'San Carlos Campus',7,'Extension Program in Celebration of the International Women\'s Month Celebration','Extension','BJMP San Carlos City, Pangasinan','Teachers and Students',29,2025,'2026-08-30 13:11:14',NULL),(381,'80abca12351b218e8c72203c4079d7c69c73b1521896de0d275d00d166a0ba0d','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',29,29,'San Carlos Campus',7,'Utilization of Carbonized Rice Hull as Soil Amendment for Rice Farming in Cabeldatan, Basista, Pangasinan','Extension','Cabeldatan, Basista, Pangasinan','Students',28,2025,'2026-08-30 13:11:14',NULL),(382,'41e22746f3bf17e64db3b97c366278fe351b34a8de0900223935ebb4ac21cae3','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',29,30,'San Carlos Campus',7,'Vermicomposting: Waster turning into Black Gold','Extension','Cabeldatan, Basista, Pangasinan','Students',28,2025,'2026-08-30 13:11:14',NULL),(383,'ab631a51f87197d5fe7f22d6888c53955f86d1a620f1c59378a0c37aac89b524','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',29,31,'San Carlos Campus',7,'Handmade with Love: A Bilao Workshop Experience','Extension','Roxas, San Carlos City, Pangasinan','Students',16,2025,'2026-08-30 13:11:14',NULL),(384,'84cc2cdf4bc382b5f2ed402805fbd24c3ec18a9781c7d8340ac0bee69682f5aa','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',29,32,'San Carlos Campus',7,'Nutriblock: Empowering the Ruminants Farmers in Natural Way','Extension','Patacbo, Basista, Pangasinan','Students',28,2025,'2026-08-30 13:11:14',NULL),(385,'48aecdb0724eec6ccbe212f4945d656bdc8d486750ed9249ad500f4e65519d24','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',29,33,'San Carlos Campus',7,'Enhancing the Swine Production and Calibrating Biosecurity Protocol of Backyard Hog Raisers in Calobaoan, San Carlos City, Pangasinan','Extension','Calobaoan, San Carlos City, Pangasinan','Students',28,2025,'2026-08-30 13:11:14',NULL),(386,'f1b043d4453c1ed008e32f9dc6037d20333004b691c6de9b2a6c852fd8a93c75','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',29,34,'San Carlos Campus',7,'AGRIHATCH: Empowering Farmers with DIY Incubator','Extension','Capataan, San Carlos City, Pangasinan','Students',28,2025,'2026-08-30 13:11:14',NULL),(387,'2e1f1333f0016208b59acebfa50406528ba96bd852dfc3d4445fecf6e8b93b31','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',29,35,'San Carlos Campus',7,'Grow More, Spend Less: The FPJ/FFJ Concoction','Extension','Doyong, San Carlos City, Pangasinan','Students',28,2025,'2026-08-30 13:11:14',NULL),(388,'13c4c0d96d4565c7b530d1ebdba43e06d8c30c3260cafc4ffdaa89b9aec5ce1c','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',30,1,'Sta. Maria Campus',8,'Mushroom Culture Media Preparation Training','Extension','PSU Sta. Maria Campus, DA- BAR','Students, Teachers, Farmers, Women',NULL,NULL,'2026-08-30 13:11:14',NULL),(389,'9df6503a318f71d76112bd9ba8808fc6e71c74384bd1c8f9c3fc2eb651244b1f','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',30,2,'Sta. Maria Campus',8,'Outdoor Mushroom Cultivation Training','Extension','PSU Sta. Maria Campus, DA- BAR','Students, Teachers, Farmers, Women',NULL,NULL,'2026-08-30 13:11:14',NULL),(390,'ccc078e61e61dd6cd55d58e19054962fdcea502ad4ecdb32da6472a86669889b','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',30,3,'Sta. Maria Campus',8,'Technical Assistance on Bamboo Propagation','Extension','PSU Sta. Maria Campus, LGU, DENR','Farmers, students',NULL,NULL,'2026-08-30 13:11:14',NULL),(391,'e4fd17b7622d54fbfa07eef0ec22c049c860f94908c3e637abd486d542e6e507','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',30,4,'Sta. Maria Campus',8,'Water Hyacinth Management & Utilization','Outreach','PSU Sta. Maria Campus, LGU, DENR','Women\'s groups, Students, Teachers',NULL,NULL,'2026-08-30 13:11:14',NULL),(392,'ff127cb0debf085923fd0b94556d1d8a0ff1c27cc7b0f1501c78eeb6e16cf9dc','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',30,5,'Sta. Maria Campus',8,'Community River Clean-up Drive','Outreach','PSU Sta. Maria Campus, LGU Sta. Maria, Local Communities','Students, Teachers, Residents, Youth',NULL,NULL,'2026-08-30 13:11:14',NULL),(393,'4ec43535bc4778374de55c96113e94f62b29f8b17c1218a87d16fb66ee1c7bbe','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',30,6,'Sta. Maria Campus',8,'Mangrove Planting & Coastal Resource Management','Outreach','PSU Sta. Maria Campus, DENR, Local Fisherfolk, LGU','Fisherfolk, Students, Teachers, Youth, Women',NULL,NULL,'2026-08-30 13:11:14',NULL),(394,'5baafd962033a8731e5722f0e99565db15c4bd6d72540a5a78f5e1b217137a7b','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',30,7,'Sta. Maria Campus',8,'Tilapia & Ornamental Fish Culture Training','Extension','PSU Sta. Maria Campus, BFAR','Students, Farmers, Fisherfolk, Teachers',NULL,NULL,'2026-08-30 13:11:14',NULL),(395,'306bc010d165baf9395ecef5a3436c7d015cb06e0b41ea45745353a48ca32025','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',30,8,'Sta. Maria Campus',8,'Seaweed Processing & Value-adding Workshop','Extension','PSU Sta. Maria Campus, DA- BAR, BFAR','Women\'s groups, Students, Teachers',NULL,NULL,'2026-08-30 13:11:14',NULL),(396,'189ef806b2f2da8268f6ddafca0b478dc713301a8bb63f6c8c55f1016af52d31','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',30,9,'Sta. Maria Campus',8,'Organic Vegetable Gardening Project','Outreach','PSU Sta. Maria Campus, LGU Sta. Maria, Local Farmers','Students, Women, Farmers, Youth',NULL,NULL,'2026-08-30 13:11:14',NULL),(397,'1ba7ff5874b7bcdae9ceba0b6870683d81b6590747ece813c1086ba0d7abef4a','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',30,10,'Sta. Maria Campus',8,'Goat Production & Management Training','Extension','PSU Sta. Maria Campus, DA, Local Farmers','Farmers, Students, Teachers',NULL,NULL,'2026-08-30 13:11:14',NULL),(398,'b5ed8f538e6946d806593f2e63ab59b964fb4c8560770d93860ca2e2ffbb90e5','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',31,11,'Sta. Maria Campus',8,'Coastal Clean-up & Marine Conservation Drive','Outreach','PSU Sta. Maria Campus, LGU Sta. Maria, DENR, Fisherfolk Assoc.','Students, Teachers, Fisherfolk, Residents',NULL,NULL,'2026-08-30 13:11:14',NULL),(399,'56ab9ade4ae51729a69b676577b8a0c48c8bd50902d4446b970e93fca40419c4','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',31,12,'Sta. Maria Campus',8,'Herbal Medicine Preparation Seminar','Outreach','PSU Sta. Maria Campus, DOH, LGU','Women, Elderly, Students, Teachers',NULL,NULL,'2026-08-30 13:11:14',NULL),(400,'28e01592af5d69ceedb882dc1847e4315d9d3e33b299925dc85d43de1c2d7fb0','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',31,13,'Sta. Maria Campus',8,'Feeding Program for Malnourished Children','Outreach','PSU Sta. Maria Campus, LGU Sta. Maria, Local NGOs','Women, Elderly, Students, Teachers',NULL,NULL,'2026-08-30 13:11:14',NULL),(401,'29c74560ddb269cd67cb1f17cac6e2bc8673ffb1a69f64a5df910fa1c173c663','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',31,14,'Sta. Maria Campus',8,'Disaster Preparedness & First Aid Training','Outreach','PSU Sta. Maria Campus, Red Cross, LGU','Students, Teachers, Health Workers, Youth',NULL,NULL,'2026-08-30 13:11:14',NULL),(402,'75f2bc35ef905f304eed32157cf5540bccad84ebe65c4559b25bd81c3690b41a','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',31,1,'Urdaneta Campus',2,'Project 3xtesible: MalasakIT with a Heart','Extension','Community Frontliners of Binalonan, Pangasinan','Faculty Members',12,2020,'2026-08-30 13:11:14',NULL),(403,'7908b4261f96693a76008ff8b56d0f5a8b46aa73f405db826c81bbf3994edc21','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',31,2,'Urdaneta Campus',2,'Targeting the Crux of the Interpersonal, Linguistic and Bodily-Kinesthetic Intelligences of OSY of Villasis, Pangasinan','Extension','Brgy. Unzad, Villasis, Pangasinan','Faculty Members',7,2021,'2026-08-30 13:11:14',NULL),(404,'978c29ce686302723a992cc9d20c9d2fcd8326a277f3aa9874d00a600938cd1c','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',31,3,'Urdaneta Campus',2,'Exploiting the Power of Montessori Approach and Creative Learning Experience in Sharpening the Teaching Pedagogy of Amagbagan','Extension','Brgy. Amagbagan, Sison, Pangasinan','Faculty Members',16,2021,'2026-08-30 13:11:14',NULL),(405,'05ec94fc7a228dd088b88842b22dce681d38de530389bae2886adeea15ac4882','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',32,4,'Urdaneta Campus',2,'CEA Community Development Program for Our Lady of Lourdes Parish, Salasa, Bugallon, Pangasinan','Extension','Our Lady of Lourdes Parish, Salasa, Bugallon, Pangasinan','Faculty Members',20,2021,'2026-08-30 13:11:14',NULL),(406,'8ba73ebc8e8d38e293d7883e04595949c971a31b2db5492fac59926291e90555','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',32,5,'Urdaneta Campus',2,'CEA Community Development Program - Brgy. Mauban, Balungao, Pangasinan','Extension','Brgy. Mauban, Balungao, Pangasinan','Faculty Members',20,2021,'2026-08-30 13:11:14',NULL),(407,'fb391d09089f75cfa7615901dcba70791fb62cc71083ce919be472ad7d1f93e9','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',32,6,'Urdaneta Campus',2,'Project i-MATH: Training for Teaching and Learning Mathematics in a Flexible Learning Environment','Extension','Tuliao National High School, Sta. Barbara, Pangasinan','Faculty Members',15,2021,'2026-08-30 13:11:14',NULL),(408,'09a5798c968c7367c09b29c8b6e4fb3a5883a2d68462e4db1a0b055960f224e7','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',32,7,'Urdaneta Campus',2,'Welding Skills Training (NC1- Plate Welding)','Extension','Brgy. Amagbagan, Sison, Pangasinan','Faculty Members',20,2021,'2026-08-30 13:11:14',NULL),(409,'4955b2bde4faf1d28667a885324548328973721d1c06573a87e3fea6e6166368','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',32,8,'Urdaneta Campus',2,'ICT Technology Transfer in Flexible Learning Modality and Community Governance Productivity','Extension','Tuliao National High School; Brgy. Tuliao LGU','Faculty Members',16,2022,'2026-08-30 13:11:14',NULL),(410,'eb4b94f59a8bc493370ddc71e6c572b74c02b1f305f443e44054b8262e600559','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',32,9,'Urdaneta Campus',2,'Computer Literacy Training for Parents in the Digital Age','Extension','Tuliao National High School; Brgy. Tuliao LGU','Faculty Members',16,2022,'2026-08-30 13:11:14',NULL),(411,'c221ec8b5f46dace8c1cafabfd5ca6aedb3e9e5b619beb016b3d0a553f878b40','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',32,10,'Urdaneta Campus',2,'Civil Engineering Department Community Development Program in Barangay Amagbagan, Sisan, Pangasinan','Extension','Brgy. Amagbagan, Sison, Pangasinan','Faculty Members',10,2022,'2026-08-30 13:11:14',NULL),(412,'7e9efd37ac01bc038ceac9f54a588fcb20a76436bb1c47c623048513e5ed38cd','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',33,11,'Urdaneta Campus',2,'Design of Prototype Model structures for Pangasinan Small-Scale Salt Maker Phase 2','Extension','LGU of Bani, Pangasinan','Faculty Members',5,2022,'2026-08-30 13:11:14',NULL),(413,'c6d6ce8dcd2eeecf33e3e524ad4c539d06ce348843fc37f98335476d53671d6a','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',33,12,'Urdaneta Campus',2,'3D modeling and printing workshop','Extension','Urdaneta City National High School','Faculty Members',5,2022,'2026-08-30 13:11:14',NULL),(414,'9cd104d46ba1fee8191fe0bd85b55c379920b54eb62abac927dc8129b7fad1a5','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',33,13,'Urdaneta Campus',2,'Exploring the Power of Montessori Approach and Creative Learning Experiences in Sharpening the Teaching Pedagogy of Amagbagan Child Development Center (Phase 2)','Extension','Brgy. Amagbagan, Sison, Pangasinan','Faculty Members',16,2022,'2026-08-30 13:11:14',NULL),(415,'e0940fae2254fbc61169931c8db0799a7ec50ac800bac4e0d15f6aa7fd604bbe','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',33,14,'Urdaneta Campus',2,'Kalinga: A Psychosocial support program for Medical Front liners at Rural Health Unit - Sison, Pangasinan','Extension','LGU of Sison, Pangasinan (Sison-RHU)','Faculty Members',15,2022,'2026-08-30 13:11:14',NULL),(416,'73f1610898ba1573945185e8f4c8f8c06e887f10975c14fd6b72bf3ef0602a50','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',33,15,'Urdaneta Campus',2,'Munting Silid Aklatan Project for Amagbagan Child Development Center','Extension','Brgy. Amagbagan, Sison, Pangasinan','Faculty Members',5,2022,'2026-08-30 13:11:14',NULL),(417,'38959f656277d09088d9477051a91b63fe316cbc9ca998f19c441a997785b2dc','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',34,16,'Urdaneta Campus',2,'ICT Technology Transfer in Flexible Learning Modality and Community Governance','Extension','Tuliao National High School; Brgy. Tuliao LGU','Faculty Members',10,2023,'2026-08-30 13:11:14',NULL),(418,'1eb58918fdcc41ebbe13a1c8336f3a4ae8bd6fae10f2f7737c7f887395ce5c5b','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',34,17,'Urdaneta Campus',2,'Computer Literacy Training for Parents in the Digital Age','Extension','Tuliao National High School; Brgy. Tuliao LGU','Faculty Members',10,2023,'2026-08-30 13:11:14',NULL),(419,'82df78251a60ba6f29e2a0fb0ff39a827a4cba0480d9af86c4cf3beb0f6bf2b7','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',34,18,'Urdaneta Campus',2,'PROGRAM: Project 3B2S (Basa, Bilang, Bibo, Sulat, Siyensiya): Extension Program for Barangay Amagbagan, Sison, Pangasinan (Year 1)','Extension','Brgy. Amagbagan, Sison, Pangasinan','Faculty Members',36,2024,'2026-08-30 13:11:14',NULL),(420,'bbd22c4ef9edd21304ce7fb583e8eedb821073d6638a93213c7e3e081c315fdc','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',34,19,'Urdaneta Campus',2,'PROJECT: Mathematics, Science and Research for Educators, Administrators and Youth (Mas Ready) Project','Extension','Urdaneta City National High School','Faculty Members',13,2024,'2026-08-30 13:11:14',NULL),(421,'f8a5b6b71d8e0a368361f1872f437b872427e671bfe056d49be28b313717536f','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',34,20,'Urdaneta Campus',2,'Metal Industry Advancement: M.E. Technology Transfer for Mud Guard Molding in San Carlos City, Pangasinan','Extension','Brgy. Doyong, San Carlos, Pangasinan','Faculty Members',10,2024,'2026-08-30 13:11:14',NULL),(422,'1d80789984d1e3270b516a5eef3cc0832501689a7e0ab0417899e88a0c529693','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',34,21,'Urdaneta Campus',2,'Unlocking Digital Skills: A Computer Literacy Training Workshop for Local Government Unit of Sta. Maria, Pangasinan','Extension','LGU of Sta. Maria, Pangasinan','Faculty Members',20,2024,'2026-08-30 13:11:14',NULL),(423,'aa2f7676e0469805507a890993955e7fdf9812c6e518c16bb8df79b0e4a8c247','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',35,22,'Urdaneta Campus',2,'Learning Management System for Mataas na Paaralang Juan C. Laya TVL- CSS-ICT','Extension','Mataas na Paaralang Juan C. Laya TVL- CSS-ICT, San Manuel, Pangasinan','Faculty Members',12,2024,'2026-08-30 13:11:14',NULL),(424,'0545906f5ffefd011b6a8a2d409f97bf5687ccd551d109e256da1d08efd3ebb2','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',35,1,'School Of Advanced Studies',NULL,'Youth Development: Enhancing Adversity Knowledge in Facing Generational Problem','Outreach','Municipality of San Jacinto, Pangasinan','4Ps and Out of School Youth',15,2024,'2026-08-30 13:11:14',NULL),(425,'8fd68c256cf54a8973fb081fe7dee21a86e5adf99851d9e9a69e6a4fc51933e2','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',35,2,'School Of Advanced Studies',NULL,'iCAREer: Restarting a Career Journey','Outreach','BJMP Urdaneta City','Persons Deprieved of Liberty',10,2025,'2026-08-30 13:11:14',NULL),(426,'7a509b630a2136c9046ec4012f177802daaa31ae5fbb5151c9e13baaee6e012e','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',35,3,'School Of Advanced Studies',NULL,'Capacity Building on Mental Health Advocacy','Outreach','L.E.A.D Academy of Urbiztondo','School Personnel',10,2025,'2026-08-30 13:11:14',NULL),(427,'8d3a68e4569b085d833e32e7550c0faadd351cbbc69b766ddb1550f539702d49','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',35,4,'School Of Advanced Studies',NULL,'Hope in Action Webinar Series: Empowering Educators and Counselors in Suicide Prevention and Crisis Management','Outreach','PSU-SAS','Guidance Counselors',8,2025,'2026-08-30 13:11:14',NULL),(428,'0836a710687e61284270a73d07e694f7d65eddd09a03deec2953a00ff72f03d6','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',36,1,'Open University Systems',NULL,'Orientation on Gender and Development (GAD) Mandates For Empowering Fish Farmers, Processors, and Traders','Extension','Barangay Caloocan Norte, Binmaley, Pangasinan','fish farmers, processors, and traders',30,2025,'2026-08-30 13:11:14',NULL),(429,'8410ae623bc97e1db3d8b584ae213aeab6eb9b92f568452801ae3b2bda482cb9','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',36,2,'Open University Systems',NULL,'Orientation on Gender and Development (GAD) Mandates For Empowering 4Ps','Extension','Barangay Poblacion Lingayen, Pangasinan','4Ps',30,2025,'2026-08-30 13:11:14',NULL),(430,'9e41b696e05cf96204b34c22bd4a38857ec479150148cf78feda492be725a31f','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',36,3,'Open University Systems',NULL,'Orientation on Gender and Development (GAD) Mandates For Empowering Persons Deprived of Liberty','Extension','Pangasinan Provincial Jail','PDL',30,2025,'2026-08-30 13:11:14',NULL),(431,'38a2cadf01abaa6a5dc2113adec42d9c365799b00adceddf4e01f728f6a80261','data-request-covp-urdaneta-leo-villanueva-2020-2025-SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf',36,4,'Open University Systems',NULL,'Orientation on Gender and Development (GAD) Mandates For Empowering Indigenuos Women','Extension','Sitio Mapita, Barangay Laoag, Aguilar Pangasinan','IP Women',30,2025,'2026-08-30 13:11:14',NULL);
/*!40000 ALTER TABLE `historical_activities` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `interests`
--

DROP TABLE IF EXISTS `interests`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `interests` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `interests`
--

LOCK TABLES `interests` WRITE;
/*!40000 ALTER TABLE `interests` DISABLE KEYS */;
INSERT INTO `interests` VALUES (7,'Arts & Culture'),(4,'Community Development'),(5,'Disaster Response'),(2,'Education & Literacy'),(1,'Environment'),(3,'Health & Wellness'),(8,'Sports & Recreation'),(6,'Technology & Digital');
/*!40000 ALTER TABLE `interests` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `milestones`
--

DROP TABLE IF EXISTS `milestones`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `milestones` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `event_id` int(11) NOT NULL,
  `filename` varchar(255) NOT NULL,
  `upload_path` varchar(500) DEFAULT NULL,
  `category` varchar(100) DEFAULT NULL,
  `uploaded_by_id` int(11) DEFAULT NULL,
  `uploaded_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `event_id` (`event_id`),
  KEY `fk_milestones_uploaded_by` (`uploaded_by_id`),
  CONSTRAINT `fk_milestones_uploaded_by` FOREIGN KEY (`uploaded_by_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
  CONSTRAINT `milestones_ibfk_1` FOREIGN KEY (`event_id`) REFERENCES `events` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `milestones`
--

LOCK TABLES `milestones` WRITE;
/*!40000 ALTER TABLE `milestones` DISABLE KEYS */;
INSERT INTO `milestones` VALUES (1,4,'download (2).jpg','uploads/milestones/48ca478c9331471ea8af5c2b1acc0375.jpg','photo',NULL,'2026-09-07 23:42:36');
/*!40000 ALTER TABLE `milestones` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `notifications`
--

DROP TABLE IF EXISTS `notifications`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `notifications` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `title` varchar(160) NOT NULL,
  `message` text NOT NULL,
  `notification_type` varchar(40) DEFAULT NULL,
  `related_event_id` int(11) DEFAULT NULL,
  `is_read` tinyint(1) NOT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `related_event_id` (`related_event_id`),
  KEY `ix_notifications_user_id` (`user_id`),
  CONSTRAINT `notifications_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `notifications_ibfk_2` FOREIGN KEY (`related_event_id`) REFERENCES `events` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `notifications`
--

LOCK TABLES `notifications` WRITE;
/*!40000 ALTER TABLE `notifications` DISABLE KEYS */;
INSERT INTO `notifications` VALUES (1,4,'New registration: Youth Coding Mentor','Student Volunteer registered for \"Youth Coding Mentor\".','registration',1,0,'2026-09-02 22:22:13'),(2,6,'Reactivation request: Student Volunteer','Student Volunteer (student@psu.edu) requested reactivation of their deactivated account.','reactivation_request',NULL,1,'2026-09-03 05:05:43'),(3,4,'Category changed: laro','The Gaming category was removed. Your activity was changed to General; please choose a new category.','category_changed',NULL,0,'2026-09-03 05:10:48');
/*!40000 ALTER TABLE `notifications` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `recommendation_logs`
--

DROP TABLE IF EXISTS `recommendation_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recommendation_logs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `event_id` int(11) NOT NULL,
  `similarity_score` float NOT NULL,
  `timestamp` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `event_id` (`event_id`),
  CONSTRAINT `recommendation_logs_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `recommendation_logs_ibfk_2` FOREIGN KEY (`event_id`) REFERENCES `events` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=327 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recommendation_logs`
--

LOCK TABLES `recommendation_logs` WRITE;
/*!40000 ALTER TABLE `recommendation_logs` DISABLE KEYS */;
INSERT INTO `recommendation_logs` VALUES (1,1,6,0.5,'2026-09-02 22:21:45'),(2,1,9,0.4714,'2026-09-02 22:21:45'),(3,1,1,0.3651,'2026-09-02 22:21:45'),(4,1,4,0.3651,'2026-09-02 22:21:45'),(5,1,2,0.2357,'2026-09-02 22:21:45'),(6,1,1,0.5151,'2026-09-02 22:22:00'),(7,1,9,0.4714,'2026-09-02 22:22:00'),(8,1,4,0.3651,'2026-09-02 22:22:00'),(9,1,9,0.4714,'2026-09-02 22:22:18'),(10,1,4,0.3651,'2026-09-02 22:22:18'),(11,1,2,0.2357,'2026-09-02 22:22:18'),(12,1,9,0.4714,'2026-09-02 22:22:25'),(13,1,4,0.3651,'2026-09-02 22:22:25'),(14,1,2,0.2357,'2026-09-02 22:22:25'),(15,1,3,0.2041,'2026-09-02 22:22:25'),(16,1,8,0.2041,'2026-09-02 22:22:25'),(17,1,9,0.4714,'2026-09-02 22:30:03'),(18,1,4,0.3651,'2026-09-02 22:30:03'),(19,1,2,0.2357,'2026-09-02 22:30:03'),(20,1,3,0.2041,'2026-09-02 22:30:03'),(21,1,8,0.2041,'2026-09-02 22:30:03'),(22,1,9,0.4714,'2026-09-02 22:30:12'),(23,1,4,0.3651,'2026-09-02 22:30:12'),(24,1,2,0.2357,'2026-09-02 22:30:12'),(25,1,3,0.2041,'2026-09-02 22:30:12'),(26,1,8,0.2041,'2026-09-02 22:30:12'),(27,1,9,0.4714,'2026-09-02 22:31:54'),(28,1,4,0.3651,'2026-09-02 22:31:54'),(29,1,2,0.2357,'2026-09-02 22:31:54'),(30,1,3,0.2041,'2026-09-02 22:31:54'),(31,1,8,0.2041,'2026-09-02 22:31:54'),(32,1,9,0.4714,'2026-09-02 22:31:55'),(33,1,4,0.3651,'2026-09-02 22:31:55'),(34,1,2,0.2357,'2026-09-02 22:31:55'),(35,1,3,0.2041,'2026-09-02 22:31:55'),(36,1,8,0.2041,'2026-09-02 22:31:55'),(37,1,9,0.4714,'2026-09-02 22:31:56'),(38,1,4,0.3651,'2026-09-02 22:31:56'),(39,1,2,0.2357,'2026-09-02 22:31:56'),(40,1,3,0.2041,'2026-09-02 22:31:56'),(41,1,8,0.2041,'2026-09-02 22:31:56'),(42,1,9,0.4714,'2026-09-02 22:56:14'),(43,1,4,0.3651,'2026-09-02 22:56:14'),(44,1,2,0.2357,'2026-09-02 22:56:14'),(45,1,3,0.2041,'2026-09-02 22:56:14'),(46,1,8,0.2041,'2026-09-02 22:56:14'),(47,1,9,0.4714,'2026-09-03 01:24:21'),(48,1,4,0.3651,'2026-09-03 01:24:21'),(49,1,2,0.2357,'2026-09-03 01:24:21'),(50,1,3,0.2041,'2026-09-03 01:24:21'),(51,1,8,0.2041,'2026-09-03 01:24:21'),(52,1,9,0.4714,'2026-09-03 01:24:49'),(53,1,4,0.3651,'2026-09-03 01:24:49'),(54,1,2,0.2357,'2026-09-03 01:24:49'),(55,1,9,0.4714,'2026-09-03 01:24:59'),(56,1,4,0.3651,'2026-09-03 01:24:59'),(57,1,2,0.2357,'2026-09-03 01:24:59'),(58,1,3,0.2041,'2026-09-03 01:24:59'),(59,1,8,0.2041,'2026-09-03 01:24:59'),(60,1,9,0.4714,'2026-09-03 01:25:07'),(61,1,4,0.3651,'2026-09-03 01:25:07'),(62,1,2,0.2357,'2026-09-03 01:25:07'),(63,1,9,0.4714,'2026-09-03 01:25:18'),(64,1,4,0.3651,'2026-09-03 01:25:18'),(65,1,2,0.2357,'2026-09-03 01:25:18'),(66,1,3,0.2041,'2026-09-03 01:25:18'),(67,1,8,0.2041,'2026-09-03 01:25:18'),(68,1,9,0.4714,'2026-09-03 01:30:38'),(69,1,4,0.3651,'2026-09-03 01:30:38'),(70,1,2,0.2357,'2026-09-03 01:30:38'),(71,1,3,0.2041,'2026-09-03 01:30:38'),(72,1,8,0.2041,'2026-09-03 01:30:38'),(73,1,9,0.4714,'2026-09-03 01:30:38'),(74,1,4,0.3651,'2026-09-03 01:30:38'),(75,1,2,0.2357,'2026-09-03 01:30:38'),(76,1,3,0.2041,'2026-09-03 01:30:38'),(77,1,8,0.2041,'2026-09-03 01:30:38'),(78,1,9,0.4714,'2026-09-03 01:30:54'),(79,1,9,0.4714,'2026-09-03 01:30:54'),(80,1,4,0.3651,'2026-09-03 01:30:54'),(81,1,2,0.2357,'2026-09-03 01:30:54'),(82,1,4,0.3651,'2026-09-03 01:30:54'),(83,1,2,0.2357,'2026-09-03 01:30:54'),(84,1,9,0.4714,'2026-09-03 01:30:55'),(85,1,4,0.3651,'2026-09-03 01:30:55'),(86,1,2,0.2357,'2026-09-03 01:30:55'),(87,1,9,0.4714,'2026-09-03 01:31:32'),(88,1,9,0.4714,'2026-09-03 01:31:32'),(89,1,4,0.3651,'2026-09-03 01:31:32'),(90,1,2,0.2357,'2026-09-03 01:31:32'),(91,1,4,0.3651,'2026-09-03 01:31:32'),(92,1,3,0.2041,'2026-09-03 01:31:32'),(93,1,8,0.2041,'2026-09-03 01:31:32'),(94,1,2,0.2357,'2026-09-03 01:31:32'),(95,1,3,0.2041,'2026-09-03 01:31:32'),(96,1,8,0.2041,'2026-09-03 01:31:32'),(97,1,9,0.4714,'2026-09-03 01:31:33'),(98,1,4,0.3651,'2026-09-03 01:31:33'),(99,1,2,0.2357,'2026-09-03 01:31:33'),(100,1,3,0.2041,'2026-09-03 01:31:33'),(101,1,8,0.2041,'2026-09-03 01:31:33'),(102,1,9,0.4714,'2026-09-03 01:31:53'),(103,1,9,0.4714,'2026-09-03 01:31:53'),(104,1,4,0.3651,'2026-09-03 01:31:53'),(105,1,4,0.3651,'2026-09-03 01:31:53'),(106,1,2,0.2357,'2026-09-03 01:31:53'),(107,1,2,0.2357,'2026-09-03 01:31:53'),(108,1,9,0.4714,'2026-09-03 01:31:54'),(109,1,4,0.3651,'2026-09-03 01:31:54'),(110,1,2,0.2357,'2026-09-03 01:31:54'),(111,1,9,0.4714,'2026-09-03 01:48:01'),(112,1,4,0.3651,'2026-09-03 01:48:01'),(113,1,2,0.2357,'2026-09-03 01:48:01'),(114,1,3,0.2041,'2026-09-03 01:48:01'),(115,1,8,0.2041,'2026-09-03 01:48:01'),(116,1,9,0.4714,'2026-09-03 01:48:02'),(117,1,4,0.3651,'2026-09-03 01:48:02'),(118,1,2,0.2357,'2026-09-03 01:48:02'),(119,1,3,0.2041,'2026-09-03 01:48:02'),(120,1,8,0.2041,'2026-09-03 01:48:02'),(121,1,9,0.4714,'2026-09-03 01:49:37'),(122,1,4,0.3651,'2026-09-03 01:49:37'),(123,1,2,0.2357,'2026-09-03 01:49:37'),(124,1,3,0.2041,'2026-09-03 01:49:37'),(125,1,8,0.2041,'2026-09-03 01:49:37'),(126,1,9,0.4714,'2026-09-03 01:50:21'),(127,1,4,0.3651,'2026-09-03 01:50:21'),(128,1,2,0.2357,'2026-09-03 01:50:21'),(129,1,3,0.2041,'2026-09-03 01:50:21'),(130,1,8,0.2041,'2026-09-03 01:50:21'),(131,1,9,0.4714,'2026-09-03 01:50:46'),(132,1,4,0.3651,'2026-09-03 01:50:46'),(133,1,2,0.2357,'2026-09-03 01:50:46'),(134,1,3,0.2041,'2026-09-03 01:50:46'),(135,1,8,0.2041,'2026-09-03 01:50:46'),(136,1,9,0.4714,'2026-09-03 01:51:12'),(137,1,4,0.3651,'2026-09-03 01:51:12'),(138,1,2,0.2357,'2026-09-03 01:51:12'),(139,1,3,0.2041,'2026-09-03 01:51:12'),(140,1,8,0.2041,'2026-09-03 01:51:12'),(141,1,9,0.4714,'2026-09-03 04:05:31'),(142,1,4,0.3651,'2026-09-03 04:05:31'),(143,1,2,0.2357,'2026-09-03 04:05:31'),(144,1,3,0.2041,'2026-09-03 04:05:31'),(145,1,8,0.2041,'2026-09-03 04:05:31'),(146,1,9,0.4714,'2026-09-03 04:06:56'),(147,1,4,0.3651,'2026-09-03 04:06:56'),(148,1,2,0.2357,'2026-09-03 04:06:56'),(149,1,3,0.2041,'2026-09-03 04:06:56'),(150,1,8,0.2041,'2026-09-03 04:06:56'),(151,1,9,0.4714,'2026-09-03 04:08:07'),(152,1,4,0.3651,'2026-09-03 04:08:07'),(153,1,2,0.2357,'2026-09-03 04:08:07'),(154,1,3,0.2041,'2026-09-03 04:08:07'),(155,1,8,0.2041,'2026-09-03 04:08:07'),(156,1,9,0.4714,'2026-09-03 04:18:14'),(157,1,4,0.3651,'2026-09-03 04:18:14'),(158,1,2,0.2357,'2026-09-03 04:18:14'),(159,1,3,0.2041,'2026-09-03 04:18:14'),(160,1,8,0.2041,'2026-09-03 04:18:14'),(161,1,9,0.4714,'2026-09-03 04:19:40'),(162,1,4,0.3651,'2026-09-03 04:19:41'),(163,1,2,0.2357,'2026-09-03 04:19:41'),(164,1,3,0.2041,'2026-09-03 04:19:41'),(165,1,8,0.2041,'2026-09-03 04:19:41'),(166,1,9,0.4714,'2026-09-03 04:19:47'),(167,1,4,0.3651,'2026-09-03 04:19:47'),(168,1,2,0.2357,'2026-09-03 04:19:47'),(169,1,9,0.4714,'2026-09-03 04:20:17'),(170,1,4,0.3651,'2026-09-03 04:20:17'),(171,1,2,0.2357,'2026-09-03 04:20:17'),(172,1,3,0.2041,'2026-09-03 04:20:17'),(173,1,8,0.2041,'2026-09-03 04:20:17'),(174,1,9,0.4714,'2026-09-03 05:04:28'),(175,1,4,0.3651,'2026-09-03 05:04:28'),(176,1,2,0.2357,'2026-09-03 05:04:28'),(177,1,3,0.2041,'2026-09-03 05:04:28'),(178,1,8,0.2041,'2026-09-03 05:04:28'),(179,1,9,0.4714,'2026-09-03 05:06:52'),(180,1,4,0.3651,'2026-09-03 05:06:52'),(181,1,2,0.2357,'2026-09-03 05:06:52'),(182,1,3,0.2041,'2026-09-03 05:06:52'),(183,1,8,0.2041,'2026-09-03 05:06:52'),(184,1,9,0.4714,'2026-09-03 05:07:05'),(185,1,4,0.3651,'2026-09-03 05:07:05'),(186,1,2,0.2357,'2026-09-03 05:07:05'),(188,1,9,0.4714,'2026-09-03 05:37:19'),(189,1,4,0.3651,'2026-09-03 05:37:19'),(190,1,2,0.2357,'2026-09-03 05:37:19'),(191,1,3,0.2041,'2026-09-03 05:37:19'),(193,1,9,0.4714,'2026-09-03 05:37:36'),(194,1,4,0.3651,'2026-09-03 05:37:36'),(196,1,9,0.4714,'2026-09-03 05:37:39'),(197,1,4,0.3651,'2026-09-03 05:37:39'),(198,1,2,0.2357,'2026-09-03 05:37:39'),(199,1,3,0.2041,'2026-09-03 05:37:39'),(201,1,9,0.4714,'2026-09-03 05:37:41'),(202,1,4,0.3651,'2026-09-03 05:37:41'),(204,1,9,0.4714,'2026-09-03 05:39:45'),(205,1,4,0.3651,'2026-09-03 05:39:45'),(206,1,2,0.2357,'2026-09-03 05:39:45'),(207,1,3,0.2041,'2026-09-03 05:39:45'),(208,1,9,0.4714,'2026-09-03 06:41:26'),(209,1,4,0.3651,'2026-09-03 06:41:26'),(210,1,2,0.2357,'2026-09-03 06:41:26'),(211,1,3,0.2041,'2026-09-03 06:41:26'),(212,1,8,0.2041,'2026-09-03 06:41:26'),(213,1,9,0.4714,'2026-09-03 06:41:38'),(214,1,4,0.3651,'2026-09-03 06:41:38'),(215,1,2,0.2357,'2026-09-03 06:41:38'),(216,1,9,0.4714,'2026-09-03 06:41:39'),(217,1,4,0.3651,'2026-09-03 06:41:39'),(218,1,2,0.2357,'2026-09-03 06:41:39'),(219,1,3,0.2041,'2026-09-03 06:41:39'),(220,1,8,0.2041,'2026-09-03 06:41:39'),(221,1,9,0.4714,'2026-09-03 06:41:41'),(222,1,4,0.3651,'2026-09-03 06:41:41'),(223,1,2,0.2357,'2026-09-03 06:41:41'),(224,1,9,0.4714,'2026-09-03 06:42:03'),(225,1,4,0.3651,'2026-09-03 06:42:03'),(226,1,2,0.2357,'2026-09-03 06:42:03'),(227,1,3,0.2041,'2026-09-03 06:42:03'),(228,1,8,0.2041,'2026-09-03 06:42:03'),(229,1,9,0.4714,'2026-09-03 06:42:35'),(230,1,4,0.3651,'2026-09-03 06:42:35'),(231,1,2,0.2357,'2026-09-03 06:42:35'),(232,1,9,0.4714,'2026-09-03 06:42:38'),(233,1,4,0.3651,'2026-09-03 06:42:38'),(234,1,2,0.2357,'2026-09-03 06:42:38'),(235,1,3,0.2041,'2026-09-03 06:42:38'),(236,1,8,0.2041,'2026-09-03 06:42:38'),(237,1,9,0.4714,'2026-09-03 06:42:43'),(238,1,4,0.3651,'2026-09-03 06:42:43'),(239,1,2,0.2357,'2026-09-03 06:42:43'),(240,1,3,0.2041,'2026-09-03 06:42:43'),(241,1,8,0.2041,'2026-09-03 06:42:43'),(242,1,9,0.4714,'2026-09-03 06:42:49'),(243,1,4,0.3651,'2026-09-03 06:42:49'),(244,1,2,0.2357,'2026-09-03 06:42:49'),(245,1,9,0.4714,'2026-09-03 09:09:23'),(246,1,4,0.3651,'2026-09-03 09:09:23'),(247,1,2,0.2357,'2026-09-03 09:09:23'),(248,1,3,0.2041,'2026-09-03 09:09:23'),(249,1,8,0.2041,'2026-09-03 09:09:23'),(250,1,9,0.4714,'2026-09-03 09:10:53'),(251,1,4,0.3651,'2026-09-03 09:10:53'),(252,1,8,0.3541,'2026-09-03 09:10:53'),(253,1,9,0.4714,'2026-09-03 09:10:55'),(254,1,4,0.3651,'2026-09-03 09:10:55'),(255,1,8,0.3541,'2026-09-03 09:10:55'),(256,1,2,0.2357,'2026-09-03 09:10:55'),(257,1,3,0.2041,'2026-09-03 09:10:55'),(258,1,9,0.4714,'2026-09-03 09:13:19'),(259,1,4,0.3651,'2026-09-03 09:13:19'),(260,1,8,0.3541,'2026-09-03 09:13:19'),(261,1,2,0.2357,'2026-09-03 09:13:19'),(262,1,3,0.2041,'2026-09-03 09:13:19'),(263,1,9,0.4714,'2026-09-03 09:13:30'),(264,1,4,0.3651,'2026-09-03 09:13:30'),(265,1,8,0.3541,'2026-09-03 09:13:30'),(266,1,2,0.2357,'2026-09-03 09:13:30'),(267,1,3,0.2041,'2026-09-03 09:13:30'),(268,7,5,0.3536,'2026-09-03 09:28:02'),(269,7,8,0.3536,'2026-09-03 09:28:02'),(270,7,1,0,'2026-09-03 09:28:02'),(271,7,3,0,'2026-09-03 09:28:02'),(272,7,2,0,'2026-09-03 09:28:02'),(273,7,5,0.3536,'2026-09-03 09:28:28'),(274,7,8,0.3536,'2026-09-03 09:28:28'),(275,7,1,0,'2026-09-03 09:28:28'),(276,7,3,0,'2026-09-03 09:28:28'),(277,7,2,0,'2026-09-03 09:28:28'),(278,7,8,0.5036,'2026-09-03 09:30:47'),(279,7,1,0,'2026-09-03 09:30:47'),(280,7,3,0,'2026-09-03 09:30:47'),(281,7,2,0,'2026-09-03 09:30:47'),(282,7,4,0,'2026-09-03 09:30:47'),(283,1,9,0.4714,'2026-09-03 09:34:33'),(284,1,4,0.3651,'2026-09-03 09:34:33'),(285,1,8,0.3541,'2026-09-03 09:34:33'),(286,1,2,0.2357,'2026-09-03 09:34:33'),(287,1,3,0.2041,'2026-09-03 09:34:33'),(288,1,9,0.4714,'2026-09-03 09:35:33'),(289,1,4,0.3651,'2026-09-03 09:35:33'),(290,1,8,0.3541,'2026-09-03 09:35:33'),(291,1,2,0.2357,'2026-09-03 09:35:33'),(292,1,3,0.2041,'2026-09-03 09:35:33'),(293,1,9,0.4714,'2026-09-03 09:37:42'),(294,1,8,0.3541,'2026-09-03 09:37:42'),(295,1,2,0.2357,'2026-09-03 09:37:42'),(296,1,3,0.2041,'2026-09-03 09:37:42'),(297,1,9,0.4714,'2026-09-03 09:38:01'),(298,1,8,0.3541,'2026-09-03 09:38:01'),(299,1,2,0.2357,'2026-09-03 09:38:01'),(300,1,3,0.2041,'2026-09-03 09:38:01'),(301,1,9,0.4714,'2026-09-03 10:10:29'),(302,1,8,0.3541,'2026-09-03 10:10:29'),(303,1,2,0.2357,'2026-09-03 10:10:29'),(304,1,3,0.2041,'2026-09-03 10:10:29'),(305,1,9,0.4714,'2026-09-03 10:10:47'),(306,1,8,0.3541,'2026-09-03 10:10:47'),(307,1,2,0.2357,'2026-09-03 10:10:47'),(308,1,9,0.4714,'2026-09-03 10:10:49'),(309,1,8,0.3541,'2026-09-03 10:10:49'),(310,1,2,0.2357,'2026-09-03 10:10:49'),(311,1,3,0.2041,'2026-09-03 10:10:49'),(312,1,9,0.4714,'2026-09-07 16:04:09'),(313,1,8,0.3541,'2026-09-07 16:04:09'),(314,1,2,0.2357,'2026-09-07 16:04:09'),(315,1,3,0.2041,'2026-09-07 16:04:09'),(316,1,9,0.4714,'2026-09-07 16:04:28'),(317,1,8,0.3541,'2026-09-07 16:04:28'),(318,1,2,0.2357,'2026-09-07 16:04:28'),(319,1,3,0.2041,'2026-09-07 16:04:28'),(320,1,9,0.4714,'2026-09-07 16:04:30'),(321,1,8,0.3541,'2026-09-07 16:04:30'),(322,1,2,0.2357,'2026-09-07 16:04:30'),(323,1,9,0.4714,'2026-09-07 16:04:48'),(324,1,8,0.3541,'2026-09-07 16:04:48'),(325,1,2,0.2357,'2026-09-07 16:04:48'),(326,1,3,0.2041,'2026-09-07 16:04:48');
/*!40000 ALTER TABLE `recommendation_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `registrations`
--

DROP TABLE IF EXISTS `registrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `registrations` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) DEFAULT NULL,
  `external_participant_id` int(11) DEFAULT NULL,
  `event_id` int(11) NOT NULL,
  `status` enum('pending','confirmed','completed','cancelled') DEFAULT NULL,
  `registered_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_event` (`user_id`,`event_id`),
  UNIQUE KEY `uk_external_event` (`external_participant_id`,`event_id`),
  KEY `event_id` (`event_id`),
  CONSTRAINT `registrations_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `registrations_ibfk_2` FOREIGN KEY (`external_participant_id`) REFERENCES `external_participants` (`id`) ON DELETE SET NULL,
  CONSTRAINT `registrations_ibfk_3` FOREIGN KEY (`event_id`) REFERENCES `events` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `registrations`
--

LOCK TABLES `registrations` WRITE;
/*!40000 ALTER TABLE `registrations` DISABLE KEYS */;
INSERT INTO `registrations` VALUES (1,1,NULL,6,'confirmed','2026-09-02 22:21:53'),(2,1,NULL,1,'confirmed','2026-09-02 22:22:13'),(3,1,NULL,5,'confirmed','2026-09-03 09:10:25'),(4,7,NULL,5,'confirmed','2026-09-03 09:29:17');
/*!40000 ALTER TABLE `registrations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `skills`
--

DROP TABLE IF EXISTS `skills`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `skills` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=28 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `skills`
--

LOCK TABLES `skills` WRITE;
/*!40000 ALTER TABLE `skills` DISABLE KEYS */;
INSERT INTO `skills` VALUES (17,'Agriculture'),(8,'Agriculture/Farming'),(15,'Communication'),(6,'Communication/Public Speaking'),(27,'Computer Skills'),(11,'Counseling/Psychology'),(7,'Creative Arts/Design'),(10,'Disaster Response'),(3,'Engineering/Construction'),(9,'Environmental Conservation'),(24,'First Aid'),(26,'IT'),(4,'IT/Computer Skills'),(12,'Languages/Translation'),(18,'Leadership'),(23,'Medical'),(2,'Medical/First Aid'),(19,'Organizational'),(5,'Organizational/Management'),(22,'Patience'),(20,'Physical Fitness'),(16,'Public Speaking'),(14,'Python'),(13,'Teaching'),(1,'Teaching/Tutoring'),(25,'Teamwork'),(21,'Tutoring');
/*!40000 ALTER TABLE `skills` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `system_settings`
--

DROP TABLE IF EXISTS `system_settings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `system_settings` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `key` varchar(100) NOT NULL,
  `value` text DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `key` (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_settings`
--

LOCK TABLES `system_settings` WRITE;
/*!40000 ALTER TABLE `system_settings` DISABLE KEYS */;
/*!40000 ALTER TABLE `system_settings` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user_interests`
--

DROP TABLE IF EXISTS `user_interests`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `user_interests` (
  `user_id` int(11) NOT NULL,
  `interest_id` int(11) NOT NULL,
  PRIMARY KEY (`user_id`,`interest_id`),
  KEY `interest_id` (`interest_id`),
  CONSTRAINT `user_interests_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `user_interests_ibfk_2` FOREIGN KEY (`interest_id`) REFERENCES `interests` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user_interests`
--

LOCK TABLES `user_interests` WRITE;
/*!40000 ALTER TABLE `user_interests` DISABLE KEYS */;
INSERT INTO `user_interests` VALUES (1,1),(1,2),(1,6),(2,1),(2,2),(2,6),(3,1),(3,2),(3,6);
/*!40000 ALTER TABLE `user_interests` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user_skills`
--

DROP TABLE IF EXISTS `user_skills`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `user_skills` (
  `user_id` int(11) NOT NULL,
  `skill_id` int(11) NOT NULL,
  PRIMARY KEY (`user_id`,`skill_id`),
  KEY `skill_id` (`skill_id`),
  CONSTRAINT `user_skills_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `user_skills_ibfk_2` FOREIGN KEY (`skill_id`) REFERENCES `skills` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user_skills`
--

LOCK TABLES `user_skills` WRITE;
/*!40000 ALTER TABLE `user_skills` DISABLE KEYS */;
INSERT INTO `user_skills` VALUES (1,1),(1,4),(1,6),(2,1),(2,4),(2,6),(3,1),(3,4),(3,6),(7,2),(7,3);
/*!40000 ALTER TABLE `user_skills` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `email` varchar(120) NOT NULL,
  `id_number` varchar(50) DEFAULT NULL,
  `volunteer_type` varchar(20) DEFAULT NULL,
  `college_affiliation` varchar(150) DEFAULT NULL,
  `password_hash` varchar(256) NOT NULL,
  `role` enum('volunteer','coordinator','director','admin') DEFAULT NULL,
  `campus_id` int(11) DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `deactivated_at` datetime DEFAULT NULL,
  `reactivation_requested_at` datetime DEFAULT NULL,
  `profile_image_path` varchar(255) DEFAULT NULL,
  `profile_image_name` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_users_email` (`email`),
  UNIQUE KEY `ix_users_id_number` (`id_number`),
  KEY `campus_id` (`campus_id`),
  CONSTRAINT `users_ibfk_1` FOREIGN KEY (`campus_id`) REFERENCES `campuses` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (1,'Student Volunteer','student@psu.edu',NULL,NULL,NULL,'scrypt:32768:8:1$gzTYPFUexarjUavc$2898746d077fbc951e5a1733283904f735eead579a6bbc3a026504bce0e54628993f0ee4f310b70931fcd695e5fefaf5642060f7d42095a8bb3abf14e4295ea7','volunteer',1,1,'2026-08-30 13:04:20',NULL,NULL,NULL,NULL),(2,'Faculty Volunteer','faculty@psu.edu',NULL,NULL,NULL,'scrypt:32768:8:1$zFooG96SLdzfVFgH$d378e2accf80b5e93fa5813c588a78f4faca07a5ed48ca46c515700d59cc0f44702ac7a62242e4db3478a7a3d8a6b39228be8f52462d3177b6f4f564224aa54b','volunteer',2,1,'2026-08-30 13:04:21',NULL,NULL,NULL,NULL),(3,'Staff Volunteer','staff@psu.edu',NULL,NULL,NULL,'scrypt:32768:8:1$5GS0fHIYBAMbZKjJ$2821136ef7a6aba9513e4392dd6879499c4dbc82fb1771da672d17b8f03ce5c8f29f84f6076d3e7b2bef88ee3125a9ab9a4fef1c879c88fe55c8e416e9a1da66','volunteer',3,1,'2026-08-30 13:04:21',NULL,NULL,NULL,NULL),(4,'Coordinator User','coordinator@psu.edu',NULL,NULL,NULL,'scrypt:32768:8:1$c1hZFv1awrFccrry$b5fcad4c6648e8a26141fada13e9713625a3eabf99e47f49fc308e6b59641af437d588d9e18767b1231381c62dafe58da1fbc558ac1387d45f64924c0dba58d4','coordinator',1,1,'2026-08-30 13:04:22',NULL,NULL,NULL,NULL),(5,'Director User','director@psu.edu',NULL,NULL,NULL,'scrypt:32768:8:1$mAyyZNAG3gGI62NU$92b51dd16355a2682ae424bc006817026243bb5a903b29e9f069327de9e420308b47d0b018043223d4b252f261c16682aae734422bbe611e5ead80dc9499a9d6','director',1,1,'2026-08-30 13:04:22',NULL,NULL,NULL,NULL),(6,'Admin User','admin@psu.edu',NULL,NULL,NULL,'scrypt:32768:8:1$VsMIu6vzW9dC9Sji$8a685cb479b52b1591acb723bbfce95c2fae99017b500d0ee3d74faae1882cf7aadb4ad1c04330c5e39e76b7abc5b27513b3ad22ac7b986e0c22e45577bc64a9','admin',1,1,'2026-08-30 13:04:22',NULL,NULL,NULL,NULL),(7,'Aeron Berbon','aeron@psu.edu','23-ur-0642','student','College of Computing','scrypt:32768:8:1$Epkbkd09NXZqEE34$1962d3bd8b09a8fdc586836b237b5cf27ad151402db45358a2a05102d4508f4b7782f7e798f4443749dd80982cb0e7afede3ccdba286ddaffdb6d41330836df7','volunteer',2,1,'2026-09-03 09:27:41',NULL,NULL,NULL,NULL);
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `volunteer_profiles`
--

DROP TABLE IF EXISTS `volunteer_profiles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `volunteer_profiles` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `past_participation` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`past_participation`)),
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  CONSTRAINT `volunteer_profiles_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `volunteer_profiles`
--

LOCK TABLES `volunteer_profiles` WRITE;
/*!40000 ALTER TABLE `volunteer_profiles` DISABLE KEYS */;
INSERT INTO `volunteer_profiles` VALUES (1,1,'[]'),(2,2,'[]'),(3,3,'[]'),(4,7,'[]');
/*!40000 ALTER TABLE `volunteer_profiles` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping routines for database 'psu_volunteer_hub'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-09-08  0:55:18
