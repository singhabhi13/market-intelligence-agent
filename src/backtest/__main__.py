from src.backtest.engine import run


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Backtest trading rules over historical data")
    parser.add_argument("--months", type=int, default=12, help="Lookback period in months")
    parser.add_argument("--csv", action="store_true", help="Output CSV files per symbol")
    args = parser.parse_args()

    results = run(months=args.months, want_csv=args.csv)

    print(f"\n{'='*60}")
    print(f"Backtest Results ({args.months}mo lookback)")
    print(f"{'='*60}\n")

    for res in results:
        print(f"{res.symbol}:")
        print(f"  Trades: {len(res.trades)}")
        print(f"  Win rate: {res.win_rate:.1f}%")
        print(f"  Total return: {res.total_return_pct:+.2f}%")
        if res.trades:
            for t in res.trades[-5:]:
                print(f"    {t.entry_date} -> {t.exit_date}: {t.return_pct:+.2f}% ({t.reason})")
        print()

    total_trades = sum(len(r.trades) for r in results)
    avg_return = sum(r.total_return_pct for r in results) / max(len(results), 1)
    print(f"Overall: {total_trades} trades, avg return: {avg_return:+.2f}%")


if __name__ == "__main__":
    main()
