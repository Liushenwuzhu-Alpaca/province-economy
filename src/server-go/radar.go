package main

import "math"

func preprocessIndicators(raw [][]float64) [][]float64 {
	if len(raw) == 0 || len(raw[0]) == 0 {
		return raw
	}
	numRows := len(raw)
	numCols := len(raw[0])

	vals := make([][]float64, numRows)
	for i := range vals {
		vals[i] = make([]float64, numCols)
		copy(vals[i], raw[i])
	}

	cpiCol := -1
	for j := 0; j < numCols; j++ {
		sum := 0.0
		for i := 0; i < numRows; i++ {
			sum += vals[i][j]
		}
		avg := sum / float64(numRows)
		if avg > 95 && avg < 105 {
			cpiCol = j
			break
		}
	}
	if cpiCol >= 0 {
		for i := 0; i < numRows; i++ {
			vals[i][cpiCol] = math.Abs(vals[i][cpiCol] - 100.0)
		}
	}

	unempCol := -1
	for j := 0; j < numCols; j++ {
		if j == cpiCol {
			continue
		}
		sum := 0.0
		for i := 0; i < numRows; i++ {
			sum += vals[i][j]
		}
		avg := sum / float64(numRows)
		if avg > 0 && avg < 10 {
			unempCol = j
			break
		}
	}

	for _, col := range []int{cpiCol, unempCol} {
		if col < 0 || col >= numCols {
			continue
		}
		colMax := vals[0][col]
		for i := 1; i < numRows; i++ {
			if vals[i][col] > colMax {
				colMax = vals[i][col]
			}
		}
		for i := 0; i < numRows; i++ {
			vals[i][col] = colMax - vals[i][col]
		}
	}

	for j := 0; j < numCols; j++ {
		colMin := vals[0][j]
		colMax := vals[0][j]
		for i := 1; i < numRows; i++ {
			if vals[i][j] < colMin {
				colMin = vals[i][j]
			}
			if vals[i][j] > colMax {
				colMax = vals[i][j]
			}
		}
		if colMax-colMin < 1e-10 {
			for i := 0; i < numRows; i++ {
				vals[i][j] = 0.5
			}
		} else {
			for i := 0; i < numRows; i++ {
				vals[i][j] = (vals[i][j] - colMin) / (colMax - colMin)
			}
		}
	}

	return vals
}
