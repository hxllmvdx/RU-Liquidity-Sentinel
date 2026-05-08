proto:
	bash scripts/generate_proto.sh

backend:
	bash scripts/run_backend.sh

ml:
	bash scripts/run_ml_services.sh

frontend:
	bash scripts/run_frontend.sh

backtest:
	bash scripts/run_backtest.sh

seed:
	bash scripts/seed_demo_data.sh
