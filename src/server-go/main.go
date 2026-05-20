package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
)

type ScoresData struct {
	Provinces []string  `json:"provinces"`
	Scores    []float64 `json:"scores"`
	Ranks     []int     `json:"ranks"`
}

type ClustersData struct {
	Provinces []string `json:"provinces"`
	Labels    []int    `json:"labels"`
	TierNames []string `json:"tier_names"`
}

type RadarData struct {
	Provinces  []string    `json:"provinces"`
	Indicators []string    `json:"indicators"`
	Values     [][]float64 `json:"values"`
}

type RankingEntry struct {
	Province string  `json:"province"`
	Score    float64 `json:"score"`
	Rank     int     `json:"rank"`
}

type RankingData struct {
	Rankings []RankingEntry `json:"rankings"`
}

type AllData struct {
	Scores   ScoresData   `json:"scores"`
	Clusters ClustersData `json:"clusters"`
	Radar    RadarData    `json:"radar"`
	Ranking  RankingData  `json:"ranking"`
	GeoJSON  interface{}  `json:"geojson"`
}

type TrendPoint struct {
	Province string  `json:"province"`
	Year     int     `json:"year"`
	Score    float64 `json:"score"`
}

type TrendData struct {
	Years     []int        `json:"years"`
	Provinces []string     `json:"provinces"`
	Series    []TrendPoint `json:"series"`
}

var indicatorLabelsCN = map[string]string{
	"gdp":                     "GDP总量",
	"gdp_growth":              "GDP增速",
	"retail":                  "社零总额",
	"income":                  "人均可支配收入",
	"consumption_expenditure": "人均消费支出",
	"tertiary_share":          "第三产业占比",
	"fixed_invest":            "固定资产投资",
	"fiscal_revenue":          "财政收入",
	"cpi":                     "物价稳定度",
	"unemployment":            "就业稳定度",
}

var tierNamesByLabel = map[int]string{
	0: "第一梯队（发达型）",
	1: "第二梯队（领先型）",
	2: "第三梯队（中坚型）",
	3: "第四梯队（追赶型）",
	4: "第五梯队",
}

var analysisIndicators = []string{
	"gdp", "gdp_growth", "retail", "income", "consumption_expenditure",
	"tertiary_share", "fixed_invest", "fiscal_revenue", "cpi", "unemployment",
}

func loadScores(year int) ScoresData {
	path := fmt.Sprintf("data/results/%d_pca/scores.csv", year)
	f, err := os.Open(path)
	if err != nil {
		return ScoresData{}
	}
	defer f.Close()

	records, err := readCSV(f)
	if err != nil || len(records) < 2 {
		return ScoresData{}
	}

	var data ScoresData
	for i := 1; i < len(records); i++ {
		rec := records[i]
		if len(rec) < 3 {
			continue
		}
		data.Provinces = append(data.Provinces, rec[0])
		if score, err := strconv.ParseFloat(rec[1], 64); err == nil {
			data.Scores = append(data.Scores, score)
		}
		if rank, err := strconv.Atoi(rec[2]); err == nil {
			data.Ranks = append(data.Ranks, rank)
		}
	}
	return data
}

func loadClusters(year int) ClustersData {
	path := fmt.Sprintf("data/results/%d_pca/clusters.csv", year)
	f, err := os.Open(path)
	if err != nil {
		return ClustersData{}
	}
	defer f.Close()

	records, err := readCSV(f)
	if err != nil || len(records) < 2 {
		return ClustersData{}
	}

	var data ClustersData
	for i := 1; i < len(records); i++ {
		rec := records[i]
		if len(rec) < 2 {
			continue
		}
		data.Provinces = append(data.Provinces, rec[0])
		label, _ := strconv.Atoi(rec[1])
		data.Labels = append(data.Labels, label)
		if name, ok := tierNamesByLabel[label]; ok {
			data.TierNames = append(data.TierNames, name)
		} else {
			data.TierNames = append(data.TierNames, fmt.Sprintf("梯队%d", label))
		}
	}
	return data
}

func loadRanking(year int) RankingData {
	path := fmt.Sprintf("data/results/%d_pca/scores.csv", year)
	f, err := os.Open(path)
	if err != nil {
		return RankingData{}
	}
	defer f.Close()

	records, err := readCSV(f)
	if err != nil || len(records) < 2 {
		return RankingData{}
	}

	var entries []RankingEntry
	for i := 1; i < len(records); i++ {
		rec := records[i]
		if len(rec) < 3 {
			continue
		}
		score, _ := strconv.ParseFloat(rec[1], 64)
		rank, _ := strconv.Atoi(rec[2])
		entries = append(entries, RankingEntry{
			Province: rec[0],
			Score:    score,
			Rank:     rank,
		})
	}
	return RankingData{Rankings: entries}
}

func loadRadar(year int) RadarData {
	path := fmt.Sprintf("data_cache/indicators_%d.csv", year)
	f, err := os.Open(path)
	if err != nil {
		return RadarData{}
	}
	defer f.Close()

	records, err := readCSV(f)
	if err != nil || len(records) < 2 {
		return RadarData{}
	}

	header := records[0]
	if len(header) == 0 || header[0] != "province" {
		return RadarData{}
	}

	colIdx := make(map[string]int)
	for i, col := range header {
		colIdx[col] = i
	}

	var indicatorCols []string
	for _, ind := range analysisIndicators {
		if _, ok := colIdx[ind]; ok {
			indicatorCols = append(indicatorCols, ind)
		}
	}

	var provinces []string
	var rawValues [][]float64

	for i := 1; i < len(records); i++ {
		rec := records[i]
		provinces = append(provinces, rec[0])
		var row []float64
		for _, col := range indicatorCols {
			if idx := colIdx[col]; idx < len(rec) {
				if val, err := strconv.ParseFloat(rec[idx], 64); err == nil {
					row = append(row, val)
				} else {
					row = append(row, 0.0)
				}
			} else {
				row = append(row, 0.0)
			}
		}
		rawValues = append(rawValues, row)
	}

	normed := preprocessIndicators(rawValues)

	var indicators []string
	for _, col := range indicatorCols {
		if name, ok := indicatorLabelsCN[col]; ok {
			indicators = append(indicators, name)
		} else {
			indicators = append(indicators, col)
		}
	}

	return RadarData{
		Provinces:  provinces,
		Indicators: indicators,
		Values:     normed,
	}
}

func loadGeojson() interface{} {
	path := "data_cache/china_provinces.geojson"
	f, err := os.Open(path)
	if err != nil {
		return nil
	}
	defer f.Close()

	var data interface{}
	if err := json.NewDecoder(f).Decode(&data); err != nil {
		return nil
	}
	return data
}

func loadAll(year int) AllData {
	return AllData{
		Scores:   loadScores(year),
		Clusters: loadClusters(year),
		Radar:    loadRadar(year),
		Ranking:  loadRanking(year),
		GeoJSON:  loadGeojson(),
	}
}

func loadTrend() TrendData {
	resultsDir := "data/results"
	entries, err := os.ReadDir(resultsDir)
	if err != nil {
		return TrendData{}
	}

	var years []int
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		name := entry.Name()
		if len(name) > 4 && strings.HasSuffix(name, "_pca") {
			if y, err := strconv.Atoi(name[:4]); err == nil {
				years = append(years, y)
			}
		}
	}
	sort.Ints(years)

	provinceSet := make(map[string]bool)
	var allSeries []TrendPoint

	for _, year := range years {
		path := fmt.Sprintf("%s/%d_pca/scores.csv", resultsDir, year)
		f, err := os.Open(path)
		if err != nil {
			continue
		}
		records, _ := readCSV(f)
		f.Close()

		for i := 1; i < len(records); i++ {
			rec := records[i]
			if len(rec) < 3 {
				continue
			}
			score, _ := strconv.ParseFloat(rec[1], 64)
			score = float64(int(score*100)) / 100.0
			provinceSet[rec[0]] = true
			allSeries = append(allSeries, TrendPoint{
				Province: rec[0],
				Year:     year,
				Score:    score,
			})
		}
	}

	var provinces []string
	for p := range provinceSet {
		provinces = append(provinces, p)
	}
	sort.Strings(provinces)

	return TrendData{
		Years:     years,
		Provinces: provinces,
		Series:    allSeries,
	}
}

func readCSV(f *os.File) ([][]string, error) {
	data, err := io.ReadAll(f)
	if err != nil {
		return nil, err
	}

	var records [][]string
	lines := strings.Split(string(data), "\n")
	for _, line := range lines {
		line = strings.TrimSuffix(line, "\r")
		if line == "" {
			continue
		}
		records = append(records, parseCSVLine(line))
	}
	return records, nil
}

func parseCSVLine(line string) []string {
	if len(line) > 0 && line[0] == 0xEF {
		if len(line) > 2 && line[1] == 0xBB && line[2] == 0xBF {
			line = line[3:]
		}
	}
	var fields []string
	var inQuotes bool
	var field strings.Builder

	for i := 0; i < len(line); i++ {
		ch := line[i]
		if ch == '"' {
			if inQuotes && i+1 < len(line) && line[i+1] == '"' {
				field.WriteByte('"')
				i++
			} else {
				inQuotes = !inQuotes
			}
		} else if ch == ',' && !inQuotes {
			fields = append(fields, field.String())
			field.Reset()
		} else {
			field.WriteByte(ch)
		}
	}
	fields = append(fields, field.String())
	return fields
}

func handleAPIData(w http.ResponseWriter, r *http.Request) {
	yearStr := r.URL.Query().Get("year")
	year, err := strconv.Atoi(yearStr)
	if err != nil || year == 0 {
		year = 2024
	}

	data := loadAll(year)

	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	json.NewEncoder(w).Encode(data)
}

func handleAPIYears(w http.ResponseWriter, r *http.Request) {
	resultsDir := "data/results"
	entries, err := os.ReadDir(resultsDir)
	if err != nil {
		writeJSON(w, map[string][]int{"years": []int{}})
		return
	}

	var years []int
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		name := entry.Name()
		if len(name) > 4 && strings.HasSuffix(name, "_pca") {
			if y, err := strconv.Atoi(name[:4]); err == nil {
				years = append(years, y)
			}
		}
	}

	sort.Ints(years)
	writeJSON(w, map[string][]int{"years": years})
}

func handleAPITrend(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, loadTrend())
}

func writeJSON(w http.ResponseWriter, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	json.NewEncoder(w).Encode(v)
}

var staticDir = "src/server-go/static"

func serveStatic(w http.ResponseWriter, r *http.Request) {
	filePath := r.URL.Path

	prefix := "/static/"
	if strings.HasPrefix(filePath, prefix) {
		filePath = strings.TrimPrefix(filePath, prefix)
	}

	fullPath := filepath.Join(staticDir, filePath)
	f, err := os.Open(fullPath)
	if err != nil {
		http.NotFound(w, r)
		return
	}
	f.Close()

	http.ServeFile(w, r, fullPath)
}

func main() {
	mux := http.NewServeMux()

	mux.HandleFunc("GET /api/data", handleAPIData)
	mux.HandleFunc("GET /api/years", handleAPIYears)
	mux.HandleFunc("GET /api/trend", handleAPITrend)
	mux.HandleFunc("GET /static/", serveStatic)
	mux.HandleFunc("GET /", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/" {
			http.NotFound(w, r)
			return
		}
		http.ServeFile(w, r, staticDir+"/index.html")
	})

	mux.HandleFunc("OPTIONS /", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "*")
		w.WriteHeader(http.StatusOK)
	})

	println("Server starting on :8766")
	if err := http.ListenAndServe(":8766", mux); err != nil {
		fmt.Fprintf(os.Stderr, "Server error: %v\n", err)
		os.Exit(1)
	}
}
