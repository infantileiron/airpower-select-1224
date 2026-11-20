-- 调压试点节电评估：试点登记与对照配对（对照小时全站唯一）
CREATE TABLE `pilots` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `start_hour` varchar(30) NOT NULL,
  `end_hour` varchar(30) NOT NULL,
  `target_pressure` float DEFAULT NULL,
  `note` text,
  `status` varchar(20) DEFAULT NULL,
  `eval_version` int DEFAULT NULL,
  `result` json DEFAULT NULL,
  `error` text,
  `approved_by` varchar(100) DEFAULT NULL,
  `approved_at` varchar(40) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `pairings` (
  `id` int NOT NULL AUTO_INCREMENT,
  `pilot_id` int NOT NULL,
  `pilot_hour` varchar(30) NOT NULL,
  `control_hour` varchar(30) NOT NULL,
  `shift` int DEFAULT NULL,
  `machines` int DEFAULT NULL,
  `pilot_flow` float DEFAULT NULL,
  `control_flow` float DEFAULT NULL,
  `flow_diff` float DEFAULT NULL,
  `pilot_temp` float DEFAULT NULL,
  `control_temp` float DEFAULT NULL,
  `temp_diff` float DEFAULT NULL,
  `pilot_kwh` float DEFAULT NULL,
  `control_kwh` float DEFAULT NULL,
  `saving` float DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `control_hour` (`control_hour`),
  KEY `pilot_id` (`pilot_id`),
  CONSTRAINT `pairings_ibfk_1` FOREIGN KEY (`pilot_id`) REFERENCES `pilots` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
