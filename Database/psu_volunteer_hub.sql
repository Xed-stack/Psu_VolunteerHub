-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Jul 21, 2026 at 10:33 AM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `psu_volunteer_hub`
--

-- --------------------------------------------------------

--
-- Table structure for table `analytics_summaries`
--

CREATE TABLE `analytics_summaries` (
  `id` int(11) NOT NULL,
  `campus_id` int(11) DEFAULT NULL,
  `metric_type` varchar(100) NOT NULL,
  `value` float NOT NULL,
  `period` varchar(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `attendance`
--

CREATE TABLE `attendance` (
  `id` int(11) NOT NULL,
  `registration_id` int(11) DEFAULT NULL,
  `user_id` int(11) NOT NULL,
  `event_id` int(11) NOT NULL,
  `status` enum('present','absent','excused') DEFAULT NULL,
  `hours_completed` float DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `campuses`
--

CREATE TABLE `campuses` (
  `id` int(11) NOT NULL,
  `name` varchar(100) NOT NULL,
  `code` varchar(20) NOT NULL,
  `description` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `campuses`
--

INSERT INTO `campuses` (`id`, `name`, `code`, `description`) VALUES
(1, 'Lingayen', 'LINGAYEN', ''),
(2, 'Urdaneta', 'URDANETA', ''),
(3, 'Asingan', 'ASINGAN', ''),
(4, 'Bayambang', 'BAYAMBANG', ''),
(5, 'Binmaley', 'BINMALEY', ''),
(6, 'Infanta', 'INFANTA', ''),
(7, 'San Carlos', 'SANCARLOS', ''),
(8, 'Santa Maria', 'STAMARIA', ''),
(9, 'Alaminos', 'ALAMINOS', '');

-- --------------------------------------------------------

--
-- Table structure for table `events`
--

CREATE TABLE `events` (
  `id` int(11) NOT NULL,
  `title` varchar(200) NOT NULL,
  `description` text NOT NULL,
  `date` datetime NOT NULL,
  `end_date` datetime DEFAULT NULL,
  `category` varchar(50) DEFAULT NULL,
  `location` varchar(500) DEFAULT NULL,
  `slots` int(11) DEFAULT NULL,
  `campus_id` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `events`
--

INSERT INTO `events` (`id`, `title`, `description`, `date`, `end_date`, `category`, `location`, `slots`, `campus_id`) VALUES
(1, 'Youth Coding Mentor', 'Help Grade 6 students at San Carlos Central School learn basic Python and logic.', '2026-07-28 15:49:32', NULL, 'Technology', '', 20, 1),
(2, 'Green Campus Initiative', 'Participate in our monthly tree planting and sustainable landscaping project.', '2026-08-04 15:49:32', NULL, 'Environment', '', 50, 1),
(3, 'Community Food Drive', 'Help organize and distribute relief packages to affected local barangays.', '2026-07-31 15:49:32', NULL, 'Community', '', 30, 2),
(4, 'Rural Literacy Program', 'Teach foundational reading and mathematics to children in remote communities.', '2026-08-11 15:49:32', NULL, 'Education', '', 15, 1),
(5, 'Disaster Response Training', 'Participate in basic first aid and disaster preparedness workshop.', '2026-07-26 15:49:32', NULL, 'Health', '', 40, 3),
(6, 'Community IT Support Workshop', 'Help bridge the digital divide by teaching elderly residents how to use modern tools.', '2026-08-20 15:49:32', NULL, 'Technology', '', 25, 4),
(7, 'Coastal Cleanup Drive', 'Monthly environmental drive to preserve the Lingayen coastline.', '2026-07-24 15:49:32', NULL, 'Environment', '', 100, 1),
(8, 'Community Wellness Fair', 'Assist medical personnel in organizing a free health mission.', '2026-09-04 15:49:32', NULL, 'Health', '', 60, 7),
(9, 'Sustainable Farming Demo', 'Learn about organic cultivation and irrigation management.', '2026-09-19 15:49:32', NULL, 'Environment', '', 30, 8);

-- --------------------------------------------------------

--
-- Table structure for table `event_skills`
--

CREATE TABLE `event_skills` (
  `event_id` int(11) NOT NULL,
  `skill_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `event_skills`
--

INSERT INTO `event_skills` (`event_id`, `skill_id`) VALUES
(1, 1),
(1, 2),
(1, 3),
(1, 4),
(2, 5),
(2, 6),
(2, 7),
(3, 3),
(3, 8),
(3, 9),
(4, 1),
(4, 3),
(4, 10),
(4, 11),
(5, 12),
(5, 13),
(5, 14),
(5, 15),
(6, 1),
(6, 3),
(6, 11),
(6, 16),
(6, 17),
(7, 5),
(7, 9),
(7, 15),
(8, 3),
(8, 8),
(8, 12),
(8, 13),
(9, 1),
(9, 5),
(9, 6);

-- --------------------------------------------------------

--
-- Table structure for table `interests`
--

CREATE TABLE `interests` (
  `id` int(11) NOT NULL,
  `name` varchar(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `interests`
--

INSERT INTO `interests` (`id`, `name`) VALUES
(1, 'Education'),
(3, 'Environment'),
(2, 'Technology');

-- --------------------------------------------------------

--
-- Table structure for table `milestones`
--

CREATE TABLE `milestones` (
  `id` int(11) NOT NULL,
  `event_id` int(11) NOT NULL,
  `filename` varchar(255) NOT NULL,
  `upload_path` varchar(500) DEFAULT NULL,
  `category` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `recommendation_logs`
--

CREATE TABLE `recommendation_logs` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `event_id` int(11) NOT NULL,
  `similarity_score` float NOT NULL,
  `timestamp` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `registrations`
--

CREATE TABLE `registrations` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `event_id` int(11) NOT NULL,
  `status` enum('pending','confirmed','completed','cancelled') DEFAULT NULL,
  `registered_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `skills`
--

CREATE TABLE `skills` (
  `id` int(11) NOT NULL,
  `name` varchar(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `skills`
--

INSERT INTO `skills` (`id`, `name`) VALUES
(6, 'Agriculture'),
(3, 'Communication'),
(17, 'Computer Skills'),
(14, 'Disaster Response'),
(5, 'Environmental Conservation'),
(13, 'First Aid'),
(16, 'IT'),
(7, 'Leadership'),
(12, 'Medical'),
(8, 'Organizational'),
(11, 'Patience'),
(9, 'Physical Fitness'),
(4, 'Public Speaking'),
(2, 'Python'),
(1, 'Teaching'),
(15, 'Teamwork'),
(10, 'Tutoring');

-- --------------------------------------------------------

--
-- Table structure for table `system_settings`
--

CREATE TABLE `system_settings` (
  `id` int(11) NOT NULL,
  `key` varchar(100) NOT NULL,
  `value` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` int(11) NOT NULL,
  `name` varchar(100) NOT NULL,
  `email` varchar(120) NOT NULL,
  `id_number` varchar(50) DEFAULT NULL,
  `password_hash` varchar(256) NOT NULL,
  `role` enum('volunteer','coordinator','director','admin') DEFAULT NULL,
  `campus_id` int(11) DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`id`, `name`, `email`, `id_number`, `password_hash`, `role`, `campus_id`, `is_active`, `created_at`) VALUES
(1, 'Student Volunteer', 'student@psu.edu', '', 'scrypt:32768:8:1$hfcv3XlrZS5SGlYC$98997bfa2b202762447cad2f9f6bc2782e0f2dc92ddbe915f0fa1908a3eb598dd8f394c3b6a397533eb2648c39a044baeec602e986c26763c456bebfa64a02d0', 'volunteer', 1, 1, '2026-07-21 07:49:32'),
(2, 'Faculty Volunteer', 'faculty@psu.edu', '', 'scrypt:32768:8:1$vswZGLS0oouXwk7T$0cf0fc9af20d607846dfbca05a2170a084109c4c05d33f7a7009b916704934692349e2c17f9b09ffa6ccd8fd5df0453dfdcea2b26c7ffc84ecb096387f81ba6f', 'volunteer', 2, 1, '2026-07-21 07:49:32'),
(3, 'Staff Volunteer', 'staff@psu.edu', '', 'scrypt:32768:8:1$MkW5oe2IVNHfyRom$0f42410803c6a9a1847d056e2b946da33295fcd9ce11c40061dfd40fb8f8fb0a27205d083ee8d3eedfb2b87f6c6a456e019210dfe3535bb7ac0be83eb81a5547', 'volunteer', 3, 1, '2026-07-21 07:49:33'),
(4, 'Coordinator User', 'coordinator@psu.edu', '', 'scrypt:32768:8:1$uapRf1SW4E9RwgtV$baf6aec867ae6e84e356590567faa399daa59b95af5685df44e73228a62d07e464c2d1afc8f265fce67b4586d2e76bf4aec426fce6a18ace320bc2da10f86689', 'coordinator', 1, 1, '2026-07-21 07:49:33'),
(5, 'Director User', 'director@psu.edu', '', 'scrypt:32768:8:1$xD4xRUfh10dy4TvF$4f1861a616c53d6487fc222935141a6810bf259f8f2a758fa583035429ff99b8ee6c7132c3032f2cc21b59000a19237153da3d7692ace95ae516e1995ec05a4c', 'director', 1, 1, '2026-07-21 07:49:33'),
(6, 'Admin User', 'admin@psu.edu', '', 'scrypt:32768:8:1$CzqPmuso6nh1sUUM$e15544c5f1cc47c7fad02974f11934032054e6e6d4aefd41ab3a9316d42a2b9f02218829a2156ce0806b50667b0b91f9bb5ab329bf77b5aed82e1b61306c0bf2', 'admin', 1, 1, '2026-07-21 07:49:33'),
(7, 'Anon', 'juliolalax@gmail.com', '23-UR-0667', 'scrypt:32768:8:1$CPp8IMjzwu12oO8t$d76cacdb5187178ae922745be971a71114b76b65da9c536a55f3c13f191ab3845feffcaf1d6edf60e14f5b3c936b34f20fc02d70ad376887e981b03b82423947', 'volunteer', 2, 1, '2026-07-21 07:50:31');

-- --------------------------------------------------------

--
-- Table structure for table `user_interests`
--

CREATE TABLE `user_interests` (
  `user_id` int(11) NOT NULL,
  `interest_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `user_interests`
--

INSERT INTO `user_interests` (`user_id`, `interest_id`) VALUES
(1, 1),
(1, 2),
(1, 3),
(2, 1),
(2, 2),
(2, 3),
(3, 1),
(3, 2),
(3, 3);

-- --------------------------------------------------------

--
-- Table structure for table `user_skills`
--

CREATE TABLE `user_skills` (
  `user_id` int(11) NOT NULL,
  `skill_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `user_skills`
--

INSERT INTO `user_skills` (`user_id`, `skill_id`) VALUES
(1, 1),
(1, 2),
(1, 3),
(2, 1),
(2, 2),
(2, 3),
(3, 1),
(3, 2),
(3, 3);

-- --------------------------------------------------------

--
-- Table structure for table `volunteer_profiles`
--

CREATE TABLE `volunteer_profiles` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `past_participation` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`past_participation`))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `volunteer_profiles`
--

INSERT INTO `volunteer_profiles` (`id`, `user_id`, `past_participation`) VALUES
(1, 1, '[]'),
(2, 2, '[]'),
(3, 3, '[]');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `analytics_summaries`
--
ALTER TABLE `analytics_summaries`
  ADD PRIMARY KEY (`id`),
  ADD KEY `campus_id` (`campus_id`);

--
-- Indexes for table `attendance`
--
ALTER TABLE `attendance`
  ADD PRIMARY KEY (`id`),
  ADD KEY `registration_id` (`registration_id`),
  ADD KEY `user_id` (`user_id`),
  ADD KEY `event_id` (`event_id`);

--
-- Indexes for table `campuses`
--
ALTER TABLE `campuses`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `code` (`code`);

--
-- Indexes for table `events`
--
ALTER TABLE `events`
  ADD PRIMARY KEY (`id`),
  ADD KEY `campus_id` (`campus_id`);

--
-- Indexes for table `event_skills`
--
ALTER TABLE `event_skills`
  ADD PRIMARY KEY (`event_id`,`skill_id`),
  ADD KEY `skill_id` (`skill_id`);

--
-- Indexes for table `interests`
--
ALTER TABLE `interests`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `name` (`name`);

--
-- Indexes for table `milestones`
--
ALTER TABLE `milestones`
  ADD PRIMARY KEY (`id`),
  ADD KEY `event_id` (`event_id`);

--
-- Indexes for table `recommendation_logs`
--
ALTER TABLE `recommendation_logs`
  ADD PRIMARY KEY (`id`),
  ADD KEY `user_id` (`user_id`),
  ADD KEY `event_id` (`event_id`);

--
-- Indexes for table `registrations`
--
ALTER TABLE `registrations`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uk_user_event` (`user_id`,`event_id`),
  ADD KEY `event_id` (`event_id`);

--
-- Indexes for table `skills`
--
ALTER TABLE `skills`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `name` (`name`);

--
-- Indexes for table `system_settings`
--
ALTER TABLE `system_settings`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `key` (`key`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `ix_users_email` (`email`),
  ADD KEY `campus_id` (`campus_id`);

--
-- Indexes for table `user_interests`
--
ALTER TABLE `user_interests`
  ADD PRIMARY KEY (`user_id`,`interest_id`),
  ADD KEY `interest_id` (`interest_id`);

--
-- Indexes for table `user_skills`
--
ALTER TABLE `user_skills`
  ADD PRIMARY KEY (`user_id`,`skill_id`),
  ADD KEY `skill_id` (`skill_id`);

--
-- Indexes for table `volunteer_profiles`
--
ALTER TABLE `volunteer_profiles`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `user_id` (`user_id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `analytics_summaries`
--
ALTER TABLE `analytics_summaries`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `attendance`
--
ALTER TABLE `attendance`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `campuses`
--
ALTER TABLE `campuses`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=10;

--
-- AUTO_INCREMENT for table `events`
--
ALTER TABLE `events`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=10;

--
-- AUTO_INCREMENT for table `interests`
--
ALTER TABLE `interests`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `milestones`
--
ALTER TABLE `milestones`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `recommendation_logs`
--
ALTER TABLE `recommendation_logs`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `registrations`
--
ALTER TABLE `registrations`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `skills`
--
ALTER TABLE `skills`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=18;

--
-- AUTO_INCREMENT for table `system_settings`
--
ALTER TABLE `system_settings`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=8;

--
-- AUTO_INCREMENT for table `volunteer_profiles`
--
ALTER TABLE `volunteer_profiles`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `analytics_summaries`
--
ALTER TABLE `analytics_summaries`
  ADD CONSTRAINT `analytics_summaries_ibfk_1` FOREIGN KEY (`campus_id`) REFERENCES `campuses` (`id`) ON DELETE SET NULL;

--
-- Constraints for table `attendance`
--
ALTER TABLE `attendance`
  ADD CONSTRAINT `attendance_ibfk_1` FOREIGN KEY (`registration_id`) REFERENCES `registrations` (`id`) ON DELETE SET NULL,
  ADD CONSTRAINT `attendance_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `attendance_ibfk_3` FOREIGN KEY (`event_id`) REFERENCES `events` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `events`
--
ALTER TABLE `events`
  ADD CONSTRAINT `events_ibfk_1` FOREIGN KEY (`campus_id`) REFERENCES `campuses` (`id`) ON DELETE SET NULL;

--
-- Constraints for table `event_skills`
--
ALTER TABLE `event_skills`
  ADD CONSTRAINT `event_skills_ibfk_1` FOREIGN KEY (`event_id`) REFERENCES `events` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `event_skills_ibfk_2` FOREIGN KEY (`skill_id`) REFERENCES `skills` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `milestones`
--
ALTER TABLE `milestones`
  ADD CONSTRAINT `milestones_ibfk_1` FOREIGN KEY (`event_id`) REFERENCES `events` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `recommendation_logs`
--
ALTER TABLE `recommendation_logs`
  ADD CONSTRAINT `recommendation_logs_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `recommendation_logs_ibfk_2` FOREIGN KEY (`event_id`) REFERENCES `events` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `registrations`
--
ALTER TABLE `registrations`
  ADD CONSTRAINT `registrations_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `registrations_ibfk_2` FOREIGN KEY (`event_id`) REFERENCES `events` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `users`
--
ALTER TABLE `users`
  ADD CONSTRAINT `users_ibfk_1` FOREIGN KEY (`campus_id`) REFERENCES `campuses` (`id`) ON DELETE SET NULL;

--
-- Constraints for table `user_interests`
--
ALTER TABLE `user_interests`
  ADD CONSTRAINT `user_interests_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `user_interests_ibfk_2` FOREIGN KEY (`interest_id`) REFERENCES `interests` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `user_skills`
--
ALTER TABLE `user_skills`
  ADD CONSTRAINT `user_skills_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `user_skills_ibfk_2` FOREIGN KEY (`skill_id`) REFERENCES `skills` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `volunteer_profiles`
--
ALTER TABLE `volunteer_profiles`
  ADD CONSTRAINT `volunteer_profiles_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
