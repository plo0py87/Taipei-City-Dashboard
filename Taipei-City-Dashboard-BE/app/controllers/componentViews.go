package controllers

import (
    "net/http"
    "strconv"

    "TaipeiCityDashboardBE/app/models"

    "github.com/gin-gonic/gin"
    "gorm.io/gorm"
    "github.com/lib/pq"
)
/*
RecordComponentView 記錄組件瀏覽次數
POST /api/v1/component/:id/view
*/
func RecordComponentView(c *gin.Context) {
	// 從 URL 參數取得組件 ID
	componentID, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "error", "message": "Invalid component ID"})
		return
	}

	// 確認組件是否存在
	var component models.Component
	if err := models.DBManager.Where("id = ?", componentID).First(&component).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"status":  "error",
			"message": "Failed to record view",
			"error":   err.Error(), // 傳回詳細錯誤訊息
		})
		return
	}

	// 記錄瀏覽次數
	if err := models.RecordComponentView(componentID); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"status": "error", "message": "Failed to record view"})
		return
	}

	// 取得該組件目前的瀏覽次數
	viewCount, err := models.GetComponentViewCount(componentID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"status": "error", "message": "Failed to get view count"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status": "success",
		"data": gin.H{
			"component_id": componentID,
			"view_count":   viewCount,
		},
	})
}

/*
GetTopViewedComponents 取得瀏覽次數最高的前 3 個組件
GET /api/v1/component/top-viewed
*/
func GetTopViewedComponents(c *gin.Context) {
	// 可以從 query parameter 取得要顯示的數量，預設為 3
	limitStr := c.DefaultQuery("limit", "3")
	limit, err := strconv.Atoi(limitStr)
	if err != nil || limit <= 0 || limit > 10 {
		limit = 3 // 預設值
	}

	// 取得熱門組件
	topComponents, err := models.GetTopComponentViews(limit)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"status": "error", "message": "Failed to get top viewed components"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status": "success",
		"data":   topComponents,
	})
}

/*
GetComponentViewCount 取得特定組件的瀏覽次數
GET /api/v1/component/:id/view-count
*/
func GetComponentViewCount(c *gin.Context) {
	// 從 URL 參數取得組件 ID
	componentID, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "error", "message": "Invalid component ID"})
		return
	}

	// 取得瀏覽次數
	viewCount, err := models.GetComponentViewCount(componentID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"status": "error", "message": "Failed to get view count"})
		return
	}

	// 取得組件資訊
	var component models.Component
	if err := models.DBManager.Where("id = ?", componentID).First(&component).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"status": "error", "message": "Component not found"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status": "success",
		"data": gin.H{
			"component_id":   componentID,
			"component_name": component.Name,
			"view_count":     viewCount,
		},
	})
}

func UpdateDashboardTopComponents(c *gin.Context) {
    // 1. 從 query 參數取得 limit（最多取前幾名），預設 3，範圍 1～10
    limitStr := c.DefaultQuery("limit", "3")
    limit, err := strconv.Atoi(limitStr)
    if err != nil || limit <= 0 || limit > 10 {
        limit = 3
    }

    // 2. 在 transaction 中執行更新並回傳更新後的 components
    err = models.DBManager.Transaction(func(tx *gorm.DB) error {
        var updatedComponents []int64

        // 3. SQL 裡面用 ? 作參數佔位，並在最後加上 RETURNING components
        updateSQL := `
            UPDATE dashboards
            SET
                components = ARRAY(
                    SELECT top_components.component_id
                    FROM (
                        SELECT
                            component_id,
                            COUNT(component_id) AS query_count
                        FROM
                            component_views
                        GROUP BY
                            component_id
                        ORDER BY
                            query_count DESC
                        LIMIT ?
                    ) AS top_components
                ),
                updated_at = NOW()
            WHERE
                name = '熱門組件'
            RETURNING components;
        `

        // 4. 執行 Raw SQL，並把 limit 當作參數傳入
        rows, err := tx.Raw(updateSQL, limit).Rows()
        if err != nil {
            return err
        }
        defer rows.Close()

        // 5. 把回傳的 components（陣列）掃出來
        for rows.Next() {
            var comps []int64
            if err := rows.Scan(pq.Array(&comps)); err != nil {
                return err
            }
            updatedComponents = comps
        }

        // 6. 把結果存到 Gin Context，供後續回傳 JSON 用
        c.Set("components", updatedComponents)
        return nil
    })

    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{
            "status":  "error",
            "message": "更新失敗：" + err.Error(),
        })
        return
    }

    // 7. 成功後從 Context 取出 components，並回傳給前端
    comps, _ := c.Get("components")
    c.JSON(http.StatusOK, gin.H{
        "status":     "success",
        "components": comps,
    })
}
