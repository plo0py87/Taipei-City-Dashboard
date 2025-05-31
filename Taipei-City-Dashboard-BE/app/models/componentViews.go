package models

import (
	"time"
)

/* ----- Models ----- */

// ComponentView 記錄組件被查看的每一次紀錄
type ComponentView struct {
	ID          int64     `json:"id" gorm:"column:id;autoincrement;primaryKey"`
	ComponentID int64     `json:"component_id" gorm:"column:component_id;not null;index"`
	ViewedAt    time.Time `json:"viewed_at" gorm:"column:viewed_at;type:timestamp with time zone;not null;index"`
	Component   Component `gorm:"foreignKey:ComponentID;references:ID"`
}

// ComponentViewCount 用於回傳組件瀏覽次數統計
type ComponentViewCount struct {
	ComponentID   int64  `json:"component_id"`
	ComponentName string `json:"component_name"`
	ViewCount     int64  `json:"view_count"`
}

/* ----- Handlers ----- */

// RecordComponentView 記錄組件被查看的次數
func RecordComponentView(componentID int64) error {
	// 建立新的瀏覽紀錄
	view := ComponentView{
		ComponentID: componentID,
		ViewedAt:    time.Now(),
	}

	// 儲存到資料庫
	if err := DBManager.Create(&view).Error; err != nil {
		return err
	}

	// 清理超過 24 小時的舊紀錄（可選，用於保持資料庫效能）
	// 這個可以改為定時任務執行
	go CleanOldComponentViews()

	return nil
}

// GetTopComponentViews 取得過去 24 小時內瀏覽次數最高的前 N 個組件
func GetTopComponentViews(limit int) ([]ComponentViewCount, error) {
	var results []ComponentViewCount

	// 計算 24 小時前的時間
	twentyFourHoursAgo := time.Now().Add(-24 * time.Hour)

	// 查詢過去 24 小時內的瀏覽次數，並按組件分組統計
	err := DBManager.
		Table("component_views").
		Select("component_views.component_id, components.name as component_name, COUNT(*) as view_count").
		Joins("JOIN components ON component_views.component_id = components.id").
		Where("component_views.viewed_at >= ?", twentyFourHoursAgo).
		Group("component_views.component_id, components.name").
		Order("view_count DESC").
		Limit(limit).
		Scan(&results).Error

	if err != nil {
		return nil, err
	}

	return results, nil
}

// GetComponentViewCount 取得特定組件在過去 24 小時內的瀏覽次數
func GetComponentViewCount(componentID int64) (int64, error) {
	var count int64

	// 計算 24 小時前的時間
	twentyFourHoursAgo := time.Now().Add(-24 * time.Hour)

	err := DBManager.
		Model(&ComponentView{}).
		Where("component_id = ? AND viewed_at >= ?", componentID, twentyFourHoursAgo).
		Count(&count).Error

	if err != nil {
		return 0, err
	}

	return count, nil
}

// CleanOldComponentViews 清理超過 7 天的舊瀏覽紀錄
func CleanOldComponentViews() error {
	// 保留 7 天內的資料，清理更舊的資料以維持資料庫效能
	sevenDaysAgo := time.Now().Add(-7 * 24 * time.Hour)

	return DBManager.
		Where("viewed_at < ?", sevenDaysAgo).
		Delete(&ComponentView{}).Error
}