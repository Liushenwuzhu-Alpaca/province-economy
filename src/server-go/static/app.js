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

// ---------------------------------------------------------------------------
// Initialization
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', function () {
    fetchYears();
    fetchTrendData();
    setupChatBar();
    window.addEventListener('resize', function () {
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
            switchChart(currentType);
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

function switchChart(type) {
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
            renderRadarChart(dashboardData);
            break;
        case 'ranking':
            renderRankingChart(dashboardData);
            break;
        case 'trend':
            renderTrendChart();
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

function renderRadarChart(data) {
    var provinces = data.radar.provinces;
    var indicators = data.radar.indicators;
    var values = data.radar.values;
    var scoreProvinces = data.scores.provinces;
    var scores = data.scores.scores;

    // Build province -> score map for ranking
    var scoreMap = {};
    for (var i = 0; i < scoreProvinces.length; i++) {
        scoreMap[scoreProvinces[i]] = scores[i];
    }

    // Sort provinces by score descending to find top 5
    var sortedProvinces = provinces.slice().sort(function (a, b) {
        return (scoreMap[b] || 0) - (scoreMap[a] || 0);
    });
    var top5Set = {};
    for (var t = 0; t < Math.min(5, sortedProvinces.length); t++) {
        top5Set[sortedProvinces[t]] = true;
    }

    // Build radar indicators
    var radarIndicators = [];
    for (var k = 0; k < indicators.length; k++) {
        radarIndicators.push({
            name: indicators[k],
            max: 1,
        });
    }

    // Build series data for ALL 31 provinces
    var seriesData = [];
    var legendSelected = {};
    for (var m = 0; m < provinces.length; m++) {
        var name = provinces[m];
        seriesData.push({
            value: values[m],
            name: name,
            lineStyle: { width: 2 },
            areaStyle: { opacity: 0.1 },
        });
        legendSelected[name] = !!top5Set[name];
    }

    var option = {
        backgroundColor: '#1e2a45',
        color: PROVINCE_PALETTE,
        title: {
            text: '省域经济竞争力雷达图（全部省份，点击图例切换显示）',
            left: 'center',
            top: 16,
            textStyle: {
                color: '#e0e0e0',
                fontSize: 18,
                fontWeight: 600,
            },
        },
        legend: {
            data: provinces,
            selected: legendSelected,
            bottom: 16,
            textStyle: { color: '#a0a0b8', fontSize: 12 },
        },
        radar: {
            indicator: radarIndicators,
            center: ['50%', '52%'],
            radius: '65%',
            axisName: {
                color: '#a0a0b8',
                fontSize: 11,
            },
            splitArea: {
                areaStyle: {
                    color: ['rgba(15, 52, 96, 0.3)', 'rgba(15, 52, 96, 0.15)'],
                },
            },
            splitLine: {
                lineStyle: { color: 'rgba(160, 160, 184, 0.2)' },
            },
            axisLine: {
                lineStyle: { color: 'rgba(160, 160, 184, 0.3)' },
            },
        },
        series: [{
            type: 'radar',
            data: seriesData,
        }],
    };

    currentChart.setOption(option);
}

// ---------------------------------------------------------------------------
// 4. Ranking bar chart (top 10)
// ---------------------------------------------------------------------------

function renderRankingChart(data) {
    var rankings = data.ranking.rankings;

    var sorted = rankings.slice().sort(function (a, b) {
        return b.score - a.score;
    });
    var top10 = sorted.slice(0, 10);

    var yData = [];
    var xData = [];
    var barColors = [];

    for (var i = 0; i < top10.length; i++) {
        yData.push(top10[i].province);
        xData.push(parseFloat(top10[i].score.toFixed(2)));
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

    yData.reverse();
    xData.reverse();
    barColors.reverse();

    var option = {
        backgroundColor: '#1e2a45',
        title: {
            text: '省域经济综合竞争力排名（前10）',
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
            left: 80,
            right: 40,
            top: 60,
            bottom: 40,
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
            axisLabel: { color: '#e0e0e0', fontSize: 12 },
            axisLine: { lineStyle: { color: '#2a3a5c' } },
            axisTick: { show: false },
        },
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
            barWidth: '60%',
            label: {
                show: true,
                position: 'right',
                color: '#a0a0b8',
                fontSize: 11,
                formatter: '{c} 分',
            },
        }],
    };

    currentChart.setOption(option);
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

function renderTrendChart() {
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
    var provinces = trendData.provinces;

    // Build a map: province -> {year: score}
    var dataMap = {};
    for (var i = 0; i < series.length; i++) {
        var s = series[i];
        if (!dataMap[s.province]) dataMap[s.province] = {};
        dataMap[s.province][s.year] = s.score;
    }

    // Find top 5 provinces by latest year score
    var latestYear = years[years.length - 1];
    var provinceScores = [];
    for (var p = 0; p < provinces.length; p++) {
        var name = provinces[p];
        var score = dataMap[name] && dataMap[name][latestYear] ? dataMap[name][latestYear] : 0;
        provinceScores.push({ name: name, score: score });
    }
    provinceScores.sort(function (a, b) { return b.score - a.score; });
    var top5 = provinceScores.slice(0, 5).map(function (x) { return x.name; });
    var top5Set = {};
    for (var t = 0; t < top5.length; t++) top5Set[top5[t]] = true;

    // Build series data for ECharts
    var echartsSeries = [];
    var legendData = [];
    for (var p2 = 0; p2 < provinces.length; p2++) {
        var prov = provinces[p2];
        var lineData = [];
        for (var y = 0; y < years.length; y++) {
            var val = dataMap[prov] && dataMap[prov][years[y]] !== undefined ? dataMap[prov][years[y]] : null;
            lineData.push(val);
        }
        legendData.push(prov);
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

    // Build legend.selected -- only top5 visible initially
    var legendSelected = {};
    for (var p3 = 0; p3 < provinces.length; p3++) {
        legendSelected[provinces[p3]] = !!top5Set[provinces[p3]];
    }

    var option = {
        backgroundColor: '#1e2a45',
        color: PROVINCE_PALETTE,
        title: {
            text: '省份竞争力趋势图（点击图例切换显示）',
            left: 'center',
            top: 16,
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
// Chat bar
// ---------------------------------------------------------------------------

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
    showToast('Agent 功能开发中，敬请期待...');
}

function showToast(message) {
    var toast = document.getElementById('toast');
    toast.textContent = message;
    toast.classList.add('show');

    setTimeout(function () {
        toast.classList.remove('show');
    }, 2000);
}