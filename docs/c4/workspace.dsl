workspace "RU Liquidity Sentinel" "Early warning system for RUB liquidity stress" {

  model {
    treasuryUser = person "Treasury Analyst" "Пользователь системы: казначей, риск-аналитик или участник демо-жюри."

    psbSystem = softwareSystem "RU Liquidity Sentinel" "Система раннего предупреждения стресса ликвидности рублёвого денежного рынка." {

      frontend = container "Frontend Dashboard" "Next.js web application for dashboard, modules, forecast, scenario simulator, backtest and analyst chat." "TypeScript, Next.js, React, Tailwind, shadcn/ui, Apache ECharts"

      backend = container "Go API Gateway" "REST API for frontend, orchestration layer, gRPC client for ML services, PostgreSQL/Redis integration." "Go, Gin, gRPC, sqlx" {
        apiHandlers = component "HTTP Handlers" "Accept REST requests, validate input and return JSON responses." "Gin handlers"
        services = component "Service Layer" "Coordinates gRPC, PostgreSQL, Redis and fallback logic." "Go services"
        grpcClient = component "gRPC Client" "Calls Python ML/Data and LLM services through protobuf contracts." "Go gRPC client"
        repositories = component "PostgreSQL Repositories" "Reads/writes LSI, signals, SHAP, jobs, chat history and backtest data." "sqlx repositories"
        cacheLayer = component "Redis Cache" "Caches dashboard responses and manages recalculation locks." "Redis client"
        middleware = component "HTTP Middleware" "CORS, request_id, logging, recovery and error handling." "Gin middleware"
      }

      scheduler = container "Scheduler" "Runs periodic recalculation jobs and source update tasks." "Go"

      mlService = container "Python ML/Data Service" "Parses public data, calculates M1-M5 signals, MAD normalization, LSI, SHAP, forecast, scenario and backtest." "Python, FastAPI/gRPC, pandas, scipy, scikit-learn, SHAP" {
        ingestion = component "Ingestion Parsers" "Downloads and parses CBR, Minfin, FNS and Roskazna data." "Python parsers"
        modules = component "M1-M5 Module Engine" "Calculates module features and stress signals." "pandas"
        normalization = component "MAD Normalization" "Calculates rolling 3-year MAD scores." "scipy/pandas"
        lsiEngine = component "LSI Engine" "Aggregates normalized signals into LSI 0-100." "scikit-learn"
        shapExplainer = component "SHAP Explainer" "Calculates feature and module contributions." "SHAP"
        forecast = component "Forecast Engine" "Forecasts LSI for 1, 3 and 7 days." "scikit-learn"
        scenario = component "Scenario Engine" "Runs what-if shocks and recalculates scenario LSI." "Python"
        backtest = component "Backtest Engine" "Runs historical validation on 2014, 2022 and 2023 stress episodes." "Python"
        grpcServer = component "gRPC Server" "Exposes ML service methods to Go backend." "grpcio"
      }

      llmService = container "LLM/RAG Analyst Service" "Generates auto-comments and answers analyst questions using RAG over system data." "Python, RAG, pgvector, LLM"

      postgres = container "PostgreSQL" "Stores LSI history, module signals, SHAP values, backtests, chat history, RAG documents and job statuses." "PostgreSQL, pgvector" {
        tags "Database"
      }

      redis = container "Redis" "Caches dashboard data and stores recalculation locks/job status." "Redis" {
        tags "Database"
      }

      rawStorage = container "Raw Data Storage" "Stores downloaded raw Excel/CSV/HTML files from public sources." "Filesystem or S3-compatible storage"
    }

    cbr = softwareSystem "CBR" "ЦБ РФ: RUONIA, key rate, repo auctions, reserves, liquidity data."
    minfin = softwareSystem "Ministry of Finance" "Минфин: OFZ auction results."
    nalog = softwareSystem "Federal Tax Service" "ФНС: tax calendar."
    roskazna = softwareSystem "Federal Treasury" "Росказна: treasury deposits and EKS placements."

    treasuryUser -> frontend "Uses dashboard, scenario simulator, backtest and analyst chat" "HTTPS"
    frontend -> backend "Calls REST API" "HTTP/JSON"

    backend -> mlService "Calls calculation, forecast, scenario and backtest methods" "gRPC"
    backend -> llmService "Calls analyst chat and auto-comment generation" "gRPC"
    backend -> postgres "Reads/writes calculated results, history, jobs and chat messages" "SQL"
    backend -> redis "Reads/writes cache and recalculation locks" "Redis protocol"

    scheduler -> mlService "Starts scheduled recalculation" "gRPC"
    scheduler -> postgres "Stores job status" "SQL"
    scheduler -> redis "Uses lock to prevent parallel recalculation" "Redis protocol"

    mlService -> cbr "Downloads market and liquidity data" "HTTPS"
    mlService -> minfin "Downloads OFZ auction data" "HTTPS"
    mlService -> nalog "Downloads tax calendar" "HTTPS"
    mlService -> roskazna "Downloads treasury placement data" "HTTPS"

    mlService -> postgres "Stores signals, LSI, SHAP and backtest results" "SQL"
    mlService -> rawStorage "Stores raw downloaded files" "File I/O"

    llmService -> postgres "Retrieves RAG documents, LSI summaries, SHAP explanations and chat context" "SQL / vector search"

    apiHandlers -> middleware "Uses"
    apiHandlers -> services "Calls"
    services -> grpcClient "Calls ML/LLM gRPC methods"
    services -> repositories "Reads/writes persistent data"
    services -> cacheLayer "Reads/writes cache and locks"
    grpcClient -> mlService "Calls ML methods" "gRPC"
    grpcClient -> llmService "Calls analyst methods" "gRPC"
    repositories -> postgres "Reads/writes data" "SQL"
    cacheLayer -> redis "Reads/writes cache and locks" "Redis protocol"

    grpcServer -> ingestion "Triggers data reload"
    grpcServer -> modules "Requests module signals"
    modules -> normalization "Normalizes signals"
    normalization -> lsiEngine "Provides MAD scores"
    lsiEngine -> shapExplainer "Explains model output"
    lsiEngine -> forecast "Provides current state"
    lsiEngine -> scenario "Supports scenario simulation"
    lsiEngine -> backtest "Supports historical validation"
    ingestion -> cbr "Downloads CBR data" "HTTPS"
    ingestion -> minfin "Downloads OFZ data" "HTTPS"
    ingestion -> nalog "Downloads tax calendar" "HTTPS"
    ingestion -> roskazna "Downloads treasury data" "HTTPS"
  }

  views {
    systemContext psbSystem "SystemContext" {
      include *
      autolayout lr
    }

    container psbSystem "Containers" {
      include *
      autolayout lr
    }

    component backend "GoBackendComponents" {
      include *
      autolayout lr
    }

    component mlService "PythonMLComponents" {
      include *
      autolayout lr
    }

    styles {
      element "Person" {
        shape person
        background "#0B5CAD"
        color "#FFFFFF"
      }

      element "Software System" {
        background "#0B5CAD"
        color "#FFFFFF"
      }

      element "Container" {
        background "#FFFFFF"
        color "#000000"
        stroke "#0B5CAD"
      }

      element "Database" {
        shape cylinder
        background "#FFF7ED"
        color "#000000"
        stroke "#F97316"
      }

      element "Component" {
        background "#FFFFFF"
        color "#000000"
        stroke "#F97316"
      }
    }
  }
}
