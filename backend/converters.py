import pandas as pd 
def snapshots_to_dataframe(snapshots):
    columns = [
        "product_id",
        "scraped_at",
        "current_price_minor",
        "original_price_minor",
        "in_stock",
    ]

    data = [
        {
            "product_id": s.product_id,
            "scraped_at": s.scraped_at,
            "current_price_minor": s.current_price_minor,
            "original_price_minor": s.original_price_minor,
            "in_stock": s.in_stock,
        }
        for s in snapshots
    ]

    df = pd.DataFrame(data, columns=columns)

    if not df.empty:
        df = df.sort_values("scraped_at").reset_index(drop=True)

    return df