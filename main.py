from src.data import get_indicators


def main(year: int = 2024):
    df = get_indicators(year)
    print(f"Loaded indicators for {year}: {df.shape[0]} provinces x {df.shape[1]} indicators")
    print(df.head())


if __name__ == "__main__":
    main()
