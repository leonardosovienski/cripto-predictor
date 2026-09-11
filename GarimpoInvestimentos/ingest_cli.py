"""Explicit acquisition entrypoint, without analysis or model composition."""

from GarimpoInvestimentos.arguments import parse_args


async def run():
    args = parse_args()
    from GarimpoInvestimentos.ingestion import configured_services, run_ingest

    services = configured_services()
    if args.discover is not None:
        from GarimpoInvestimentos.collectors.discovery import discover_assets

        assets = await discover_assets(top_n=min(args.discover, 20))
    elif args.assets:
        assets = [value.strip() for value in args.assets.split(",") if value.strip()]
    else:
        assets = services.settings.DEFAULT_ASSETS
    if not assets:
        raise ValueError("No acquisition assets selected")
    _, failed = await run_ingest(assets, args.mode, services=services)
    if failed:
        raise SystemExit(2)
