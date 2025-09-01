-- SQL迁移脚本：为hunt表添加缺失的列
-- SQL migration script: Add missing columns to hunt table

-- 检查并添加hunt_actions列
-- Check and add hunt_actions column
SET @sql = CASE 
    WHEN (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
          WHERE TABLE_NAME = 'hunt' 
          AND COLUMN_NAME = 'hunt_actions' 
          AND TABLE_SCHEMA = DATABASE()) = 0 
    THEN 'ALTER TABLE hunt ADD COLUMN hunt_actions INT DEFAULT 0 COMMENT ''寻找装备的次数'''
    ELSE 'SELECT ''hunt_actions column already exists'' as status'
END;

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 检查并添加daily_car_info列
-- Check and add daily_car_info column
SET @sql = CASE 
    WHEN (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
          WHERE TABLE_NAME = 'hunt' 
          AND COLUMN_NAME = 'daily_car_info' 
          AND TABLE_SCHEMA = DATABASE()) = 0 
    THEN 'ALTER TABLE hunt ADD COLUMN daily_car_info TEXT NULL COMMENT ''缓存的每日汽车信息'''
    ELSE 'SELECT ''daily_car_info column already exists'' as status'
END;

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 验证迁移结果
-- Verify migration results
SELECT 
    'hunt table columns:' as status,
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT,
    COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'hunt' 
AND TABLE_SCHEMA = DATABASE()
ORDER BY ORDINAL_POSITION;