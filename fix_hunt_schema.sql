-- Hunt Game Database Schema Fix
-- 寻宝游戏数据库结构修复脚本
-- 
-- This script adds missing columns to the hunt table that are required
-- by the current hunt.py game code.
-- 
-- Run this script in your MySQL database to fix the hunt game startup issue.

USE bavabot;  -- Change this to your actual database name

-- Add hunt_actions column if it doesn't exist
SET @sql = CASE 
    WHEN (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
          WHERE TABLE_NAME = 'hunt' 
          AND COLUMN_NAME = 'hunt_actions' 
          AND TABLE_SCHEMA = DATABASE()) = 0 
    THEN 'ALTER TABLE hunt ADD COLUMN hunt_actions INT DEFAULT 0 COMMENT ''寻找装备的次数 - Number of hunt actions'''
    ELSE 'SELECT ''hunt_actions column already exists'' as status'
END;

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add daily_car_info column if it doesn't exist
SET @sql = CASE 
    WHEN (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
          WHERE TABLE_NAME = 'hunt' 
          AND COLUMN_NAME = 'daily_car_info' 
          AND TABLE_SCHEMA = DATABASE()) = 0 
    THEN 'ALTER TABLE hunt ADD COLUMN daily_car_info TEXT NULL COMMENT ''缓存的每日汽车信息 - Cached daily car info'''
    ELSE 'SELECT ''daily_car_info column already exists'' as status'
END;

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add message_id column if it doesn't exist
SET @sql = CASE 
    WHEN (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
          WHERE TABLE_NAME = 'hunt' 
          AND COLUMN_NAME = 'message_id' 
          AND TABLE_SCHEMA = DATABASE()) = 0 
    THEN 'ALTER TABLE hunt ADD COLUMN message_id INT NULL COMMENT ''关联的消息ID - Associated message ID'''
    ELSE 'SELECT ''message_id column already exists'' as status'
END;

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add chat_id column if it doesn't exist
SET @sql = CASE 
    WHEN (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
          WHERE TABLE_NAME = 'hunt' 
          AND COLUMN_NAME = 'chat_id' 
          AND TABLE_SCHEMA = DATABASE()) = 0 
    THEN 'ALTER TABLE hunt ADD COLUMN chat_id BIGINT NULL COMMENT ''消息所在的聊天ID - Chat ID where message is located'''
    ELSE 'SELECT ''chat_id column already exists'' as status'
END;

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Verify the hunt table structure
SELECT 
    'Hunt table structure after fix:' as info,
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT,
    COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'hunt' 
AND TABLE_SCHEMA = DATABASE()
ORDER BY ORDINAL_POSITION;

-- Show success message
SELECT '✅ Hunt database schema fix completed successfully!' as result;
SELECT '🎮 The hunt game should now be able to start properly.' as next_step;
SELECT '📝 Make sure to restart your bot to apply the changes.' as note;