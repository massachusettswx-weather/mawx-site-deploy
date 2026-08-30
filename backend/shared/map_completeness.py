from __future__ import annotations

def canonical_key(product, region, forecast_hour):
    return (str(product), str(region), int(forecast_hour))

def expected_inventory(*, products, regions, forecast_hours):
    return {canonical_key(p, r, h) for h in forecast_hours for r in regions for p in products}

def work_plan_for_hour(*, completed, products, regions, forecast_hour):
    completed = set(completed)
    plan = {}
    for region in regions:
        missing = {p for p in products if canonical_key(p, region, forecast_hour) not in completed}
        if missing:
            plan[str(region)] = missing
    return plan

def region_report(*, completed, products, regions, forecast_hour):
    completed = set(completed)
    report = {}
    for region in regions:
        missing = [p for p in products if canonical_key(p, region, forecast_hour) not in completed]
        report[str(region)] = {
            "expected": len(products),
            "complete": len(products) - len(missing),
            "missing": missing,
            "is_complete": not missing,
        }
    return report

def hour_complete(*, completed, products, regions, forecast_hour):
    return not work_plan_for_hour(
        completed=completed, products=products, regions=regions, forecast_hour=forecast_hour
    )

def cycle_report(*, completed, products, regions, forecast_hours):
    completed = set(completed)
    expected = expected_inventory(products=products, regions=regions, forecast_hours=forecast_hours)
    missing = expected - completed
    hours = {}
    for hour in forecast_hours:
        rr = region_report(completed=completed, products=products, regions=regions, forecast_hour=hour)
        hours[int(hour)] = {"complete": all(x["is_complete"] for x in rr.values()), "regions": rr}
    return {
        "expected": len(expected), "complete": len(expected)-len(missing),
        "missing": len(missing), "is_complete": not missing, "hours": hours,
    }

def repair_hours(*, completed, products, regions, forecast_hours):
    return [int(h) for h in forecast_hours if not hour_complete(
        completed=completed, products=products, regions=regions, forecast_hour=h
    )]
