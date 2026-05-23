'use strict';

// ---------------------------------------------------------------------------
// Province name mapping: short name -> ECharts china map full name
// ---------------------------------------------------------------------------

var PROVINCE_NAME_MAP = {
    '北京': '北京市',
    '上海': '上海市',
    '天津': '天津市',
    '重庆': '重庆市',
    '河北': '河北省',
    '山西': '山西省',
    '辽宁': '辽宁省',
    '吉林': '吉林省',
    '黑龙江': '黑龙江省',
    '江苏': '江苏省',
    '浙江': '浙江省',
    '安徽': '安徽省',
    '福建': '福建省',
    '江西': '江西省',
    '山东': '山东省',
    '河南': '河南省',
    '湖北': '湖北省',
    '湖南': '湖南省',
    '广东': '广东省',
    '海南': '海南省',
    '四川': '四川省',
    '贵州': '贵州省',
    '云南': '云南省',
    '陕西': '陕西省',
    '甘肃': '甘肃省',
    '青海': '青海省',
    '台湾': '台湾省',
    '内蒙古': '内蒙古自治区',
    '广西': '广西壮族自治区',
    '西藏': '西藏自治区',
    '宁夏': '宁夏回族自治区',
    '新疆': '新疆维吾尔自治区',
    '香港': '香港特别行政区',
    '澳门': '澳门特别行政区',
};

function toFullName(shortName) {
    return PROVINCE_NAME_MAP[shortName] || shortName;
}

// ---------------------------------------------------------------------------
// Tier colors (label -> color)
// ---------------------------------------------------------------------------

var TIER_COLORS = {
    0: '#b8311a',
    1: '#e89c5f',
    2: '#7fb2d8',
    3: '#2c5f8d',
};

var TIER_NAMES = {
    0: '第一梯队（发达型）',
    1: '第二梯队（领先型）',
    2: '第三梯队（中坚型）',
    3: '第四梯队（追赶型）',
};

// ---------------------------------------------------------------------------
// Score colorscale (5-stop, cold to warm)
// ---------------------------------------------------------------------------

var SCORE_COLORS = ['#2c5f8d', '#7fb2d8', '#f4e8c1', '#e89c5f', '#b8311a'];

// ---------------------------------------------------------------------------
// Ranking medal colors
// ---------------------------------------------------------------------------

var RANK_GOLD = '#d4af37';
var RANK_SILVER = '#c0c0c0';
var RANK_BRONZE = '#cd7f32';
var RANK_NORMAL = '#4a7ab8';

// ---------------------------------------------------------------------------
// Province palette for multi-series charts
// ---------------------------------------------------------------------------

var PROVINCE_PALETTE = [
    '#b8311a', '#e89c5f', '#4a7ab8', '#5b8c5a',
    '#8e5a9b', '#c0793e', '#3d8e8e', '#a83279',
];

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

var currentChart = null;
var currentType = 'scoreMap';
var dashboardData = null;
var currentYear = 2024;
var trendData = null;
var pendingProvinces = null;

// ---------------------------------------------------------------------------
// Initialization
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', function () {
    initSession();
    fetchYears();
    fetchTrendData();
    setupChatBar();
    resizeChartSection();
    // Restore chat bubbles from previous session
    if (chatMessages.length > 0 && chatMessages[0].content) {
        for (var cm = 0; cm < chatMessages.length; cm++) {
            var msg = chatMessages[cm];
            if (msg.content) {
                appendChatBubble(msg.role, msg.content);
            }
        }
    }
    window.addEventListener('resize', function () {
        resizeChartSection();
        if (currentChart) {
            currentChart.resize();
        }
    });
});

function fetchData(year) {
    showLoading();
    fetch('/api/data?year=' + year)
        .then(function (response) {
            if (!response.ok) {
                throw new Error('HTTP ' + response.status);
            }
            return response.json();
        })
        .then(function (data) {
            dashboardData = data;
            currentYear = year;
            // Register China map from API GeoJSON (ECharts 5 no longer bundles maps)
            echarts.registerMap('china', data.geojson);
            hideLoading();
            var p = pendingProvinces;
            pendingProvinces = null;
            switchChart(currentType, p);
        })
        .catch(function (err) {
            hideLoading();
            showError('数据加载失败: ' + err.message);
        });
}

function fetchYears() {
    fetch('/api/years')
        .then(function (response) {
            if (!response.ok) {
                throw new Error('HTTP ' + response.status);
            }
            return response.json();
        })
        .then(function (data) {
            var years = data.years;
            var select = document.getElementById('year-select');
            for (var i = 0; i < years.length; i++) {
                var option = document.createElement('option');
                option.value = years[i];
                option.textContent = years[i] + ' 年';
                select.appendChild(option);
            }
            // Select latest year by default
            select.value = years[years.length - 1];
            currentYear = parseInt(select.value);
            select.addEventListener('change', function () {
                var newYear = parseInt(this.value);
                if (newYear !== currentYear) {
                    fetchData(newYear);
                }
            });
            // Load initial data for the default year
            fetchData(currentYear);
        })
        .catch(function (err) {
            showError('年份列表加载失败: ' + err.message);
        });
}

// ---------------------------------------------------------------------------
// Chart switching
// ---------------------------------------------------------------------------

function switchChart(type, provinces) {
    if (!dashboardData) {
        return;
    }

    var chartDom = document.getElementById('chart-container');
    if (currentChart) {
        echarts.dispose(chartDom);
        currentChart = null;
    }

    removeOverlays();

    currentChart = echarts.init(chartDom, null, { renderer: 'canvas' });
    currentType = type;

    switch (type) {
        case 'scoreMap':
            renderScoreMap(dashboardData);
            break;
        case 'tierMap':
            renderTierMap(dashboardData);
            break;
        case 'radar':
            renderRadarChart(dashboardData, provinces);
            break;
        case 'ranking':
            renderRankingChart(dashboardData, provinces);
            break;
        case 'trend':
            renderTrendChart(provinces);
            break;
    }

    updateNavButtons(type);
}

function updateNavButtons(activeType) {
    var buttons = document.querySelectorAll('.nav-btn');
    buttons.forEach(function (btn) {
        if (btn.getAttribute('data-chart') === activeType) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

// ---------------------------------------------------------------------------
// Loading / Error overlays
// ---------------------------------------------------------------------------

function showLoading() {
    var container = document.getElementById('chart-container');
    var overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.style.display = 'flex';
    }
}

function hideLoading() {
    var overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

function showError(message) {
    var container = document.getElementById('chart-container');
    removeOverlays();

    var div = document.createElement('div');
    div.className = 'error-overlay';
    div.id = 'error-overlay';
    div.innerHTML =
        '<div class="error-icon">⚠️</div>' +
        '<div class="error-msg">' + escapeHtml(message) + '</div>' +
        '<button class="retry-btn" onclick="retryFetch()">重新加载</button>';
    container.appendChild(div);
}

function removeOverlays() {
    var container = document.getElementById('chart-container');
    var errorOverlay = document.getElementById('error-overlay');
    if (errorOverlay) {
        errorOverlay.remove();
    }
    hideLoading();
}

function retryFetch() {
    removeOverlays();
    showLoading();
    fetchData(currentYear);
}

function escapeHtml(text) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}

// ---------------------------------------------------------------------------
// 1. Score heatmap map
// ---------------------------------------------------------------------------

function renderScoreMap(data) {
    var provinces = data.scores.provinces;
    var scores = data.scores.scores;

    var mapData = [];
    for (var i = 0; i < provinces.length; i++) {
        mapData.push({
            name: toFullName(provinces[i]),
            value: parseFloat(scores[i].toFixed(2)),
        });
    }

    var option = {
        backgroundColor: '#1e2a45',
        title: {
            text: '省域经济综合得分热力图',
            left: 'center',
            top: 16,
            textStyle: {
                color: '#e0e0e0',
                fontSize: 18,
                fontWeight: 600,
            },
        },
        tooltip: {
            trigger: 'item',
            formatter: function (params) {
                if (params.value === undefined || isNaN(params.value)) {
                    return params.name + '<br/>暂无数据';
                }
                return params.name + '<br/>综合得分: ' + params.value + ' 分';
            },
        },
        visualMap: {
            type: 'piecewise',
            pieces: [
                { min: 80, max: 100, label: '80-100', color: SCORE_COLORS[4] },
                { min: 60, max: 80, label: '60-80', color: SCORE_COLORS[3] },
                { min: 40, max: 60, label: '40-60', color: SCORE_COLORS[2] },
                { min: 20, max: 40, label: '20-40', color: SCORE_COLORS[1] },
                { min: 0, max: 20, label: '0-20', color: SCORE_COLORS[0] },
            ],
            left: 16,
            bottom: 24,
            textStyle: { color: '#a0a0b8', fontSize: 11 },
        },
        series: [{
            name: '综合得分',
            type: 'map',
            map: 'china',
            roam: true,
            label: {
                show: true,
                fontSize: 10,
                color: '#c0c0d0',
            },
            emphasis: {
                label: {
                    show: true,
                    fontSize: 12,
                    fontWeight: 'bold',
                    color: '#fff',
                },
                itemStyle: {
                    areaColor: '#3a5a8c',
                },
            },
            itemStyle: {
                borderColor: '#2a3a5c',
                borderWidth: 0.8,
            },
            data: mapData,
        }],
    };

    currentChart.setOption(option);
}

// ---------------------------------------------------------------------------
// 2. Cluster tier map
// ---------------------------------------------------------------------------

function renderTierMap(data) {
    var provinces = data.clusters.provinces;
    var labels = data.clusters.labels;
    var tierNames = data.clusters.tier_names;

    var mapData = [];
    for (var i = 0; i < provinces.length; i++) {
        var label = labels[i];
        mapData.push({
            name: toFullName(provinces[i]),
            value: label,
            itemStyle: {
                color: TIER_COLORS[label] || '#555555',
            },
        });
    }

    var legendData = [];
    var legendColors = [];
    for (var key in TIER_NAMES) {
        if (TIER_NAMES.hasOwnProperty(key)) {
            legendData.push(TIER_NAMES[key]);
            legendColors.push(TIER_COLORS[key]);
        }
    }

    var option = {
        backgroundColor: '#1e2a45',
        title: {
            text: '省域经济聚类梯队分布',
            left: 'center',
            top: 16,
            textStyle: {
                color: '#e0e0e0',
                fontSize: 18,
                fontWeight: 600,
            },
        },
        tooltip: {
            trigger: 'item',
            formatter: function (params) {
                var tierName = TIER_NAMES[params.value];
                if (!tierName) {
                    return params.name + '<br/>暂无数据';
                }
                return params.name + '<br/>' + tierName;
            },
        },
        series: [{
            name: '聚类梯队',
            type: 'map',
            map: 'china',
            roam: true,
            label: {
                show: true,
                fontSize: 10,
                color: '#c0c0d0',
            },
            emphasis: {
                label: {
                    show: true,
                    fontSize: 12,
                    fontWeight: 'bold',
                    color: '#fff',
                },
                itemStyle: {
                    areaColor: '#3a5a8c',
                },
            },
            itemStyle: {
                borderColor: '#2a3a5c',
                borderWidth: 0.8,
            },
            data: mapData,
        }],
    };

    var legendItems = [];
    for (var k in TIER_NAMES) {
        if (TIER_NAMES.hasOwnProperty(k)) {
            legendItems.push({
                name: TIER_NAMES[k],
                icon: 'circle',
            });
        }
    }

    option.legend = {
        data: legendItems,
        bottom: 16,
        textStyle: { color: '#a0a0b8', fontSize: 11 },
        itemWidth: 12,
        itemHeight: 12,
    };

    option.visualMap = {
        type: 'piecewise',
        pieces: [
            { value: 0, label: TIER_NAMES[0], color: TIER_COLORS[0] },
            { value: 1, label: TIER_NAMES[1], color: TIER_COLORS[1] },
            { value: 2, label: TIER_NAMES[2], color: TIER_COLORS[2] },
            { value: 3, label: TIER_NAMES[3], color: TIER_COLORS[3] },
        ],
        left: 16,
        bottom: 24,
        textStyle: { color: '#a0a0b8', fontSize: 11 },
    };

    for (var j = 0; j < mapData.length; j++) {
        delete mapData[j].itemStyle;
    }

    currentChart.setOption(option);
}

// ---------------------------------------------------------------------------
// 3. Radar chart (top 5 provinces)
// ---------------------------------------------------------------------------

function renderRadarChart(data, provinces) {
    var radarProvinces = data.radar.provinces;
    var indicators = data.radar.indicators;
    var values = data.radar.values;
    var scoreProvinces = data.scores.provinces;
    var scores = data.scores.scores;

    // Build province -> index map
    var provIndex = {};
    for (var i = 0; i < radarProvinces.length; i++) {
        provIndex[radarProvinces[i]] = i;
    }

    // Build score map for ranking
    var scoreMap = {};
    for (var j = 0; j < scoreProvinces.length; j++) {
        scoreMap[scoreProvinces[j]] = scores[j];
    }

    // Determine which provinces are selected by default
    var selectedSet = {};
    var titleText;
    if (provinces && provinces.length) {
        for (var p = 0; p < provinces.length; p++) {
            if (provIndex[provinces[p]] !== undefined) {
                selectedSet[provinces[p]] = true;
            }
        }
        if (Object.keys(selectedSet).length === 0) {
            // Fallback: top 5 by score
            var fb = radarProvinces.slice().sort(function (a, b) { return (scoreMap[b] || 0) - (scoreMap[a] || 0); });
            var fbTop = fb.slice(0, 5);
            for (var ti = 0; ti < fbTop.length; ti++) { selectedSet[fbTop[ti]] = true; }
        }
        titleText = '省域经济竞争力雷达图（默认显示: ' + Object.keys(selectedSet).join('/') + '，点击图例切换）';
    } else {
        var sorted = radarProvinces.slice().sort(function (a, b) { return (scoreMap[b] || 0) - (scoreMap[a] || 0); });
        var top5 = sorted.slice(0, 5);
        for (var t = 0; t < top5.length; t++) { selectedSet[top5[t]] = true; }
        titleText = '省域经济竞争力雷达图（默认前5名，点击图例切换）';
    }

    // Build radar indicators
    var radarIndicators = [];
    for (var k = 0; k < indicators.length; k++) {
        radarIndicators.push({ name: indicators[k], max: 1 });
    }

    // Build series data for ALL provinces, but default-select only specified ones
    var seriesData = [];
    var legendSelected = {};
    for (var m = 0; m < radarProvinces.length; m++) {
        var name = radarProvinces[m];
        seriesData.push({
            value: values[m],
            name: name,
            lineStyle: { width: 2 },
            areaStyle: { opacity: 0.1 },
        });
        legendSelected[name] = !!selectedSet[name];
    }

    var option = {
        backgroundColor: '#1e2a45',
        color: PROVINCE_PALETTE,
        title: {
            text: titleText,
            left: 'center', top: 16,
            textStyle: { color: '#e0e0e0', fontSize: 18, fontWeight: 600 },
        },
        legend: {
            data: radarProvinces,
            selected: legendSelected,
            bottom: 16,
            textStyle: { color: '#a0a0b8', fontSize: 12 },
        },
        radar: {
            indicator: radarIndicators,
            center: ['50%', '52%'],
            radius: '65%',
            axisName: { color: '#a0a0b8', fontSize: 11 },
            splitArea: { areaStyle: { color: ['rgba(15, 52, 96, 0.3)', 'rgba(15, 52, 96, 0.15)'] } },
            splitLine: { lineStyle: { color: 'rgba(160, 160, 184, 0.2)' } },
            axisLine: { lineStyle: { color: 'rgba(160, 160, 184, 0.3)' } },
        },
        series: [{ type: 'radar', data: seriesData }],
    };

    currentChart.setOption(option);
}

// ---------------------------------------------------------------------------
// 4. Ranking bar chart (top 10)
// ---------------------------------------------------------------------------

function renderRankingChart(data, provinces) {
    var rankings = data.ranking.rankings;

    var sorted = rankings.slice().sort(function (a, b) {
        return b.score - a.score;
    });
    var all = sorted; // All 31 provinces

    var yData = [];
    var xData = [];
    var barColors = [];

    for (var i = 0; i < all.length; i++) {
        yData.push(all[i].province);
        xData.push(parseFloat(all[i].score.toFixed(2)));
        if (i === 0) {
            barColors.push(RANK_GOLD);
        } else if (i === 1) {
            barColors.push(RANK_SILVER);
        } else if (i === 2) {
            barColors.push(RANK_BRONZE);
        } else {
            barColors.push(RANK_NORMAL);
        }
    }

    // Reverse so best (rank 1) is at top
    yData.reverse();
    xData.reverse();
    barColors.reverse();

    // Helper: fuzzy match province name in yData
    function findProvinceIndex(name, dataArray) {
        // Exact match first
        var idx = dataArray.indexOf(name);
        if (idx >= 0) return idx;
        // Try without suffix (e.g. "广东" matches "广东省")
        var short = name.replace(/省|市|自治区|壮族|回族|维吾尔/g, '');
        for (var fi = 0; fi < dataArray.length; fi++) {
            if (dataArray[fi].indexOf(short) === 0) return fi;
        }
        // Try contains
        for (var fj = 0; fj < dataArray.length; fj++) {
            if (dataArray[fj].indexOf(name) >= 0 || name.indexOf(dataArray[fj]) >= 0) return fj;
        }
        return -1;
    }

    // Calculate dataZoom — default show top ~10 provinces
    var viewRange = 32; // ~10 provinces out of 31
    var dzStart = 100 - viewRange;
    var dzEnd = 100;
    if (provinces && provinces.length) {
        for (var pi = 0; pi < provinces.length; pi++) {
            var idx = findProvinceIndex(provinces[pi], yData);
            if (idx >= 0) {
                var pct = (idx / (yData.length - 1)) * 100;
                dzStart = Math.max(0, pct - viewRange / 2);
                dzEnd = Math.min(100, pct + viewRange / 2);
                break;
            }
        }
    }

    var option = {
        backgroundColor: '#1e2a45',
        title: {
            text: '省域经济综合竞争力排名（全部 31 省）',
            left: 'center',
            top: 16,
            textStyle: {
                color: '#e0e0e0',
                fontSize: 18,
                fontWeight: 600,
            },
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: function (params) {
                var p = params[0];
                return p.name + '<br/>综合得分: ' + p.value + ' 分';
            },
        },
        grid: {
            left: 90,
            right: 50,
            top: 60,
            bottom: 60,
        },
        xAxis: {
            type: 'value',
            axisLabel: { color: '#a0a0b8', fontSize: 11 },
            axisLine: { lineStyle: { color: '#2a3a5c' } },
            splitLine: { lineStyle: { color: 'rgba(160, 160, 184, 0.15)' } },
        },
        yAxis: {
            type: 'category',
            data: yData,
            axisLabel: { color: '#e0e0e0', fontSize: 11 },
            axisLine: { lineStyle: { color: '#2a3a5c' } },
            axisTick: { show: false },
        },
        dataZoom: [{
            type: 'slider',
            yAxisIndex: 0,
            start: dzStart,
            end: dzEnd,
            width: 20,
            right: 4,
        }],
        series: [{
            type: 'bar',
            data: xData.map(function (val, idx) {
                return {
                    value: val,
                    itemStyle: {
                        color: barColors[idx],
                        borderRadius: [0, 4, 4, 0],
                    },
                };
            }),
            barWidth: '50%',
            label: {
                show: true,
                position: 'right',
                color: '#a0a0b8',
                fontSize: 10,
                formatter: '{c} 分',
            },
        }],
    };

    currentChart.setOption(option);

    // Fallback: dispatch dataZoom to ensure scroll takes effect after render
    if (provinces && provinces.length) {
        var targetIdx2 = null;
        for (var si = 0; si < provinces.length; si++) {
            var t2 = findProvinceIndex(provinces[si], yData);
            if (t2 >= 0) { targetIdx2 = t2; break; }
        }
        if (targetIdx2 !== null) {
            var tpct2 = (targetIdx2 / (yData.length - 1)) * 100;
            setTimeout(function() {
                currentChart.dispatchAction({
                    type: 'dataZoom',
                    dataZoomIndex: 0,
                    start: Math.max(0, tpct2 - viewRange / 2),
                    end: Math.min(100, tpct2 + viewRange / 2),
                });
            }, 50);
        }
    }
}

// ---------------------------------------------------------------------------
// 5. Trend chart (multi-year line chart via /api/trend)
// ---------------------------------------------------------------------------

function fetchTrendData() {
    fetch('/api/trend')
        .then(function (response) {
            if (!response.ok) throw new Error('HTTP ' + response.status);
            return response.json();
        })
        .then(function (data) {
            trendData = data;
        })
        .catch(function (err) {
            console.error('趋势数据加载失败: ' + err.message);
        });
}

function renderTrendChart(provinces) {
    if (!trendData) {
        currentChart.setOption({
            backgroundColor: '#1e2a45',
            title: { text: '趋势图', left: 'center', top: 'middle', textStyle: { color: '#e0e0e0' } },
            graphic: [{ type: 'text', left: 'center', top: 'middle', style: { text: '趋势数据加载中...', fontSize: 20, fill: '#6c6c8a' } }]
        });
        return;
    }

    var years = trendData.years;
    var series = trendData.series;
    var allProvinces = trendData.provinces;

    // Build a map: province -> {year: score}
    var dataMap = {};
    for (var i = 0; i < series.length; i++) {
        var s = series[i];
        if (!dataMap[s.province]) dataMap[s.province] = {};
        dataMap[s.province][s.year] = s.score;
    }

    var latestYear = years[years.length - 1];

    // Determine which provinces are selected by default
    var selectedSet = {};
    var titleText;
    if (provinces && provinces.length) {
        for (var p = 0; p < provinces.length; p++) {
            if (dataMap[provinces[p]]) {
                selectedSet[provinces[p]] = true;
            }
        }
        if (Object.keys(selectedSet).length === 0) {
            var scoresFb = [];
            for (var a = 0; a < allProvinces.length; a++) {
                var n = allProvinces[a];
                scoresFb.push({ name: n, score: dataMap[n] && dataMap[n][latestYear] ? dataMap[n][latestYear] : 0 });
            }
            scoresFb.sort(function (a, b) { return b.score - a.score; });
            var fbTop2 = scoresFb.slice(0, 5).map(function (x) { return x.name; });
            for (var fi = 0; fi < fbTop2.length; fi++) { selectedSet[fbTop2[fi]] = true; }
        }
        titleText = '省份竞争力趋势图（默认显示: ' + Object.keys(selectedSet).join('/') + '，点击图例切换）';
    } else {
        var scoresDef = [];
        for (var b = 0; b < allProvinces.length; b++) {
            var n2 = allProvinces[b];
            scoresDef.push({ name: n2, score: dataMap[n2] && dataMap[n2][latestYear] ? dataMap[n2][latestYear] : 0 });
        }
        scoresDef.sort(function (a, b) { return b.score - a.score; });
        var defaultTop5 = scoresDef.slice(0, 5).map(function (x) { return x.name; });
        for (var di = 0; di < defaultTop5.length; di++) { selectedSet[defaultTop5[di]] = true; }
        titleText = '省份竞争力趋势图（默认前5名，点击图例切换）';
    }

    // Build series data for ALL provinces, default-select only specified ones
    var echartsSeries = [];
    var legendData = [];
    var legendSelected = {};
    for (var p2 = 0; p2 < allProvinces.length; p2++) {
        var prov = allProvinces[p2];
        var lineData = [];
        for (var y = 0; y < years.length; y++) {
            var val = dataMap[prov] && dataMap[prov][years[y]] !== undefined ? dataMap[prov][years[y]] : null;
            lineData.push(val);
        }
        legendData.push(prov);
        legendSelected[prov] = !!selectedSet[prov];
        echartsSeries.push({
            name: prov,
            type: 'line',
            data: lineData,
            smooth: true,
            lineStyle: { width: 2 },
            symbol: 'circle',
            symbolSize: 4,
        });
    }

    var option = {
        backgroundColor: '#1e2a45',
        color: PROVINCE_PALETTE,
        title: {
            text: titleText,
            left: 'center', top: 16,
            textStyle: { color: '#e0e0e0', fontSize: 18, fontWeight: 600 }
        },
        tooltip: {
            trigger: 'axis',
            backgroundColor: 'rgba(30,42,69,0.9)',
            borderColor: 'rgba(160,160,184,0.3)',
            textStyle: { color: '#e0e0e0', fontSize: 13 }
        },
        legend: {
            data: legendData,
            selected: legendSelected,
            type: 'scroll',
            bottom: 8,
            textStyle: { color: '#a0a0b8', fontSize: 11 }
        },
        grid: { left: 60, right: 40, top: 70, bottom: 60 },
        xAxis: {
            type: 'category',
            data: years,
            axisLine: { lineStyle: { color: 'rgba(160,160,184,0.3)' } },
            axisLabel: { color: '#a0a0b8', fontSize: 12 }
        },
        yAxis: {
            type: 'value',
            name: '综合得分',
            min: 0,
            max: 100,
            axisLine: { lineStyle: { color: 'rgba(160,160,184,0.3)' } },
            axisLabel: { color: '#a0a0b8', fontSize: 12 },
            splitLine: { lineStyle: { color: 'rgba(160,160,184,0.1)' } }
        },
        series: echartsSeries
    };

    currentChart.setOption(option);
}

// ---------------------------------------------------------------------------
// Chat — multi-turn, SSE streaming, Markdown + KaTeX, persistent during session
// ---------------------------------------------------------------------------

var chatHistory = [];   // API history [{role, content}]
var chatMessages = [];  // UI state [{role, content, elementId}]
var chatCollapsed = true; // Start collapsed
var chatStreaming = false;
var sessionId = '';
var sseRetryCount = 0;
var sseMaxRetries = 3;

// Session persistence: generate or restore session ID
function initSession() {
    var stored = localStorage.getItem('pe_session_id');
    if (stored) {
        sessionId = stored;
    } else {
        sessionId = 'sess_' + Date.now() + '_' + Math.random().toString(36).substring(2, 10);
        localStorage.setItem('pe_session_id', sessionId);
    }
    // Restore chat messages from last session
    var savedMsgs = localStorage.getItem('pe_chat_messages');
    if (savedMsgs) {
        try {
            var parsed = JSON.parse(savedMsgs);
            if (Array.isArray(parsed)) {
                chatMessages = parsed.slice(-20);
                chatHistory = chatMessages.filter(function (m) { return m.role && m.content; });
            }
        } catch (e) { /* ignore corrupt data */ }
    }
}

function saveSession() {
    try {
        localStorage.setItem('pe_chat_messages', JSON.stringify(chatMessages.slice(-20)));
    } catch (e) { /* quota exceeded, ignore */ }
}

// Resize chart section to fill the viewport
function resizeChartSection() {
    var section = document.getElementById('chart-section');
    if (!section) return;
    // viewport height - sidebar is handled by flex, we just need the wrapper height
    var wrapper = document.getElementById('scroll-wrapper');
    if (wrapper) {
        var h = wrapper.clientHeight;
        section.style.height = h + 'px';
        section.style.minHeight = h + 'px';
    }
}

function setupChatBar() {
    var input = document.getElementById('chat-input');
    var sendBtn = document.getElementById('send-btn');

    sendBtn.addEventListener('click', handleChatSend);
    input.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
            handleChatSend();
        }
    });
}

function handleChatSend() {
    if (chatStreaming) return;

    var input = document.getElementById('chat-input');
    var sendBtn = document.getElementById('send-btn');
    var message = input.value.trim();
    if (!message) return;

    input.value = '';

    // Expand chat if collapsed
    if (chatCollapsed) {
        expandChat();
    }

    // Add user message
    appendChatBubble('user', message);

    // Add empty AI bubble
    var aiBubbleId = appendChatBubble('ai', '');

    chatStreaming = true;
    input.disabled = true;
    sendBtn.disabled = true;
    sendBtn.textContent = '思考中...';

    var fullText = '';
    var aiEl = document.getElementById(aiBubbleId);

    fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: message, history: chatHistory, session_id: sessionId }),
    })
    .then(function (response) {
        if (!response.ok) throw new Error('HTTP ' + response.status);

        var reader = response.body.getReader();
        var decoder = new TextDecoder();
        var buffer = '';

        function read() {
            reader.read().then(function (result) {
                if (result.done) {
                    finishChat(fullText);
                    return;
                }
                buffer += decoder.decode(result.value, { stream: true });

                var lines = buffer.split('\n');
                buffer = '';

                for (var i = 0; i < lines.length; i++) {
                    var line = lines[i];
                    if (line.startsWith('event: ')) {
                        var eventType = line.substring(7).trim();
                        var dataLine = '';
                        for (var j = i + 1; j < lines.length; j++) {
                            if (lines[j].startsWith('data: ')) {
                                dataLine = lines[j].substring(6);
                                break;
                            }
                        }
                        if (!dataLine) {
                            buffer = lines.slice(i).join('\n');
                            break;
                        }

                        try { var data = JSON.parse(dataLine); } catch (e) { continue; }

                        if (eventType === 'token' && data.text) {
                            fullText += data.text;
                            aiEl.innerHTML = renderMd(fullText);
                            renderKaTeX(aiEl);
                            scrollChat();
                        } else if (eventType === 'tool') {
                            // Handle show_chart: switch UI to show the chart
                            if (data.name === 'show_chart' && data.input) {
                                var chartType = data.input.chart_type || 'ranking';
                                var chartYear = data.input.year || currentYear;
                                var provinces = data.input.provinces || null;
                                // Switch year if different
                                if (chartYear !== currentYear) {
                                    pendingProvinces = provinces;
                                    var yearSelect = document.getElementById('year-select');
                                    if (yearSelect) {
                                        yearSelect.value = chartYear;
                                        fetchData(chartYear);
                                    }
                                } else {
                                    // Switch chart silently in background (don't collapse chat)
                                    _origSwitchChart(chartType, provinces);
                                    resizeChartSection();
                                }
                                aiEl.innerHTML = renderMd(fullText);
                                scrollChat();
                            } else {
                                var toolInfo = '[调用工具: ' + data.name + ']';
                                aiEl.innerHTML = renderMd(fullText) + '<div class="tool-call">' + escapeHtml(toolInfo) + '</div>';
                                scrollChat();
                            }
                        } else if (eventType === 'error') {
                            fullText = data.text || '发生错误';
                            aiEl.innerHTML = '<div class="chat-error">' + escapeHtml(fullText) + '</div>';
                        }
                    }
                }

                read();
            }).catch(function (err) {
                if (sseRetryCount < sseMaxRetries) {
                    sseRetryCount++;
                    var waitMs = 500 * Math.pow(2, sseRetryCount - 1);
                    aiEl.innerHTML = renderMd(fullText) + '<div class="tool-call">连接中断，正在重连 (' + sseRetryCount + '/' + sseMaxRetries + ')...</div>';
                    setTimeout(function () {
                        sseRetry(aiEl, aiBubbleId, message);
                    }, waitMs);
                } else {
                    if (!fullText) {
                        aiEl.innerHTML = '<div class="chat-error">连接中断，请重试</div>';
                    }
                    sseRetryCount = 0;
                    finishChat(fullText);
                }
            });

        function sseRetry(aiEl, aiBubbleId, message) {
            var fullText2 = '';
            fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message, history: chatHistory, session_id: sessionId }),
            })
            .then(function (resp2) {
                if (!resp2.ok) throw new Error('HTTP ' + resp2.status);
                var reader2 = resp2.body.getReader();
                var decoder2 = new TextDecoder();
                var buffer2 = '';

                function read2() {
                    reader2.read().then(function (result2) {
                        if (result2.done) {
                            sseRetryCount = 0;
                            finishChat(fullText2);
                            return;
                        }
                        buffer2 += decoder2.decode(result2.value, { stream: true });
                        var lines2 = buffer2.split('\n');
                        buffer2 = '';
                        for (var li = 0; li < lines2.length; li++) {
                            var l2 = lines2[li];
                            if (l2.startsWith('event: ')) {
                                var et2 = l2.substring(7).trim();
                                var dl2 = '';
                                for (var lj = li + 1; lj < lines2.length; lj++) {
                                    if (lines2[lj].startsWith('data: ')) { dl2 = lines2[lj].substring(6); break; }
                                }
                                if (!dl2) { buffer2 = lines2.slice(li).join('\n'); break; }
                                try { var d2 = JSON.parse(dl2); } catch (e) { continue; }
                                if (et2 === 'token' && d2.text) {
                                    fullText2 += d2.text;
                                    aiEl.innerHTML = renderMd(fullText2);
                                    renderKaTeX(aiEl);
                                    scrollChat();
                                } else if (et2 === 'tool' && d2.name === 'show_chart' && d2.input) {
                                    var ct = d2.input.chart_type || 'ranking';
                                    var cy = d2.input.year || currentYear;
                                    var cp = d2.input.provinces || null;
                                    if (cy !== currentYear) {
                                        pendingProvinces = cp;
                                        var ys = document.getElementById('year-select');
                                        if (ys) { ys.value = cy; fetchData(cy); }
                                    } else {
                                        _origSwitchChart(ct, cp);
                                        resizeChartSection();
                                    }
                                    aiEl.innerHTML = renderMd(fullText2);
                                    scrollChat();
                                } else if (et2 === 'tool') {
                                    aiEl.innerHTML = renderMd(fullText2) + '<div class="tool-call">[调用工具: ' + escapeHtml(d2.name) + ']</div>';
                                    scrollChat();
                                } else if (et2 === 'error') {
                                    fullText2 = d2.text || '发生错误';
                                    aiEl.innerHTML = '<div class="chat-error">' + escapeHtml(fullText2) + '</div>';
                                }
                            }
                        }
                        read2();
                    }).catch(function (err2) {
                        if (sseRetryCount < sseMaxRetries) {
                            sseRetryCount++;
                            var w2 = 500 * Math.pow(2, sseRetryCount - 1);
                            aiEl.innerHTML = renderMd(fullText2) + '<div class="tool-call">重连失败 (' + sseRetryCount + '/' + sseMaxRetries + ')...</div>';
                            setTimeout(function () { sseRetry(aiEl, aiBubbleId, message); }, w2);
                        } else {
                            aiEl.innerHTML = '<div class="chat-error">连接中断，请重试</div>';
                            sseRetryCount = 0;
                            finishChat(fullText2);
                        }
                    });
                }
                read2();
            })
            .catch(function (err2) {
                sseRetryCount = 0;
                aiEl.innerHTML = '<div class="chat-error">重连失败，请刷新重试</div>';
                finishChat(fullText2);
            });
        }
        }

        read();
    })
    .catch(function (err) {
        aiEl.innerHTML = '<div class="chat-error">请求失败</div>';
        finishChat(fullText);
    });

    function finishChat(text) {
        chatHistory.push({ role: 'user', content: message });
        if (text) {
            chatHistory.push({ role: 'assistant', content: text });
        }
        if (chatHistory.length > 20) {
            chatHistory = chatHistory.slice(-20);
        }
        chatMessages.push({ role: 'user', content: message });
        chatMessages.push({ role: 'assistant', content: text });
        saveSession();

        // Final KaTeX render
        renderKaTeX(aiEl);

        chatStreaming = false;
        input.disabled = false;
        sendBtn.disabled = false;
        sendBtn.textContent = '发送';
        input.focus();
        updateChatToggle();
    }
}

// Collapse / expand chat panel
function collapseChat() {
    chatCollapsed = true;
    document.getElementById('chat-panel').classList.add('collapsed');
    document.getElementById('chat-toggle').style.display = 'flex';
    updateChatToggle();
    resizeChartSection();
    // Scroll wrapper back to top to show chart
    document.getElementById('scroll-wrapper').scrollTop = 0;
}

function expandChat() {
    chatCollapsed = false;
    document.getElementById('chat-panel').classList.remove('collapsed');
    document.getElementById('chat-toggle').style.display = 'none';
    // Chart keeps its full height, chat appears below
    scrollChat();
}

function updateChatToggle() {
    var count = chatMessages.length;
    var countEl = document.getElementById('chat-toggle-count');
    if (countEl) {
        countEl.textContent = count > 0 ? count + ' 条对话' : '';
    }
}

// Override switchChart to collapse chat when switching charts/years
var _origSwitchChart = switchChart;
switchChart = function (type, provinces) {
    if (chatMessages.length > 0 && !chatCollapsed) {
        collapseChat();
    }
    _origSwitchChart(type, provinces);
    resizeChartSection();
};

function appendChatBubble(role, content) {
    var panel = document.getElementById('chat-messages');
    if (!panel) return '';

    var bubbleId = 'bubble-' + Date.now() + '-' + Math.random().toString(36).substring(2, 8);

    var wrapper = document.createElement('div');
    if (role === 'user') {
        wrapper.className = 'chat-question';
        wrapper.innerHTML =
            '<span class="chat-avatar chat-avatar-user">你</span>' +
            '<div class="chat-bubble chat-bubble-user">' + escapeHtml(content) + '</div>';
    } else {
        wrapper.className = 'chat-answer';
        wrapper.innerHTML =
            '<span class="chat-avatar chat-avatar-ai">AI</span>' +
            '<div class="chat-bubble chat-bubble-ai" id="' + bubbleId + '">' +
            (content ? renderMd(content) : '<span class="chat-cursor">▌</span>') +
            '</div>';
    }

    panel.appendChild(wrapper);
    scrollChat();
    return bubbleId;
}

function scrollChat() {
    var wrapper = document.getElementById('scroll-wrapper');
    if (wrapper) {
        wrapper.scrollTop = wrapper.scrollHeight;
    }
}

// Markdown + KaTeX rendering
function renderMd(text) {
    // Protect LaTeX from marked.js mangling
    var latexBlocks = [];
    var protected_ = text;

    // Protect $$...$$ (display math)
    protected_ = protected_.replace(/\$\$([\s\S]*?)\$\$/g, function (m) {
        latexBlocks.push({ display: true, content: m.slice(2, -2) });
        return 'LATEXBLOCK' + (latexBlocks.length - 1) + 'END';
    });

    // Protect $...$ (inline math)
    protected_ = protected_.replace(/\$([^\$\n]+?)\$/g, function (m) {
        latexBlocks.push({ display: false, content: m.slice(1, -1) });
        return 'LATEXBLOCK' + (latexBlocks.length - 1) + 'END';
    });

    // Protect \[...\] (display math)
    protected_ = protected_.replace(/\\\[([\s\S]*?)\\\]/g, function (m) {
        latexBlocks.push({ display: true, content: m.slice(2, -2) });
        return 'LATEXBLOCK' + (latexBlocks.length - 1) + 'END';
    });

    // Protect \(...\) (inline math)
    protected_ = protected_.replace(/\\\(([\s\S]*?)\\\)/g, function (m) {
        latexBlocks.push({ display: false, content: m.slice(2, -2) });
        return 'LATEXBLOCK' + (latexBlocks.length - 1) + 'END';
    });

    // Render markdown
    var html;
    if (typeof marked !== 'undefined' && marked.parse) {
        try { html = marked.parse(protected_); } catch (e) { html = escapeHtml(protected_); }
    } else {
        html = escapeHtml(protected_);
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\n/g, '<br>');
    }

    // Restore LaTeX placeholders
    html = html.replace(/LATEXBLOCK(\d+)END/g, function (m, idx) {
        var block = latexBlocks[parseInt(idx)];
        if (!block) return '';
        try {
            return katex.renderToString(block.content, {
                displayMode: block.display,
                throwOnError: false,
            });
        } catch (e) {
            return escapeHtml(block.content);
        }
    });

    return html;
}

// Re-render KaTeX in a DOM element (for already-rendered markdown)
function renderKaTeX(el) {
    if (typeof renderMathInElement === 'function') {
        try {
            renderMathInElement(el, {
                delimiters: [
                    { left: '$$', right: '$$', display: true },
                    { left: '$', right: '$', display: false },
                    { left: '\\[', right: '\\]', display: true },
                    { left: '\\(', right: '\\)', display: false },
                ],
                throwOnError: false,
            });
        } catch (e) { /* ignore */ }
    }
}

function showToast(message) {
    var toast = document.getElementById('toast');
    toast.textContent = message;
    toast.classList.add('show');

    setTimeout(function () {
        toast.classList.remove('show');
    }, 2000);
}