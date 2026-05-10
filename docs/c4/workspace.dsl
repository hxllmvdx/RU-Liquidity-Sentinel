workspace "RU Liquidity Sentinel" "RUB liquidity stress early warning" {

  model {
    treasuryUser = person "Treasury Analyst" "Казначей или риск-аналитик."

    psbSystem = softwareSystem "RU Liquidity Sentinel" "Раннее предупреждение стресса рублёвой ликвидности." {

      frontend = container "Web UI" "Дашборд и инструменты аналитика." "Next.js"

      backend = container "API Gateway" "REST API и orchestration layer." "Go" {
        apiHandlers = component "HTTP API" "REST endpoints." "Gin"
        services = component "Services" "Бизнес-логика." "Go"
        grpcClient = component "gRPC Client" "Вызовы Python-сервисов." "gRPC"
        repositories = component "Repositories" "Работа с PostgreSQL." "sqlx"
        cacheLayer = component "Cache" "Кэш и блокировки." "Redis"
        middleware = component "Middleware" "CORS, logging, errors." "Gin"
      }

      scheduler = container "Scheduler" "Периодический пересчёт." "Go"

      mlService = container "ML/Data Service" "Сбор данных и расчёт сигналов." "Python" {
        ingestion = component "Ingestion" "Загрузка источников." "Python"
        modules = component "M1-M5 Engine" "Фичи и сигналы." "pandas"
        normalization = component "Normalization" "MAD-нормализация." "scipy/pandas"
        lsiEngine = component "LSI Engine" "Расчёт LSI." "scikit-learn"
        shapExplainer = component "SHAP" "Объяснение вклада факторов." "SHAP"
        forecast = component "Forecast" "Прогноз LSI." "scikit-learn"
        scenario = component "Scenario" "What-if сценарии." "Python"
        backtest = component "Backtest" "Историческая проверка." "Python"
        grpcServer = component "gRPC API" "Интерфейс для Go API." "grpcio"
      }

      llmService = container "Analyst Copilot" "Комментарии и Q&A с RAG." "Python"

      postgres = container "PostgreSQL" "История LSI, сигналы, RAG, jobs." "PostgreSQL" {
        tags "Database"
      }

      redis = container "Redis" "Кэш и блокировки." "Redis" {
        tags "Database"
      }

      rawStorage = container "Raw Storage" "Сырые файлы источников." "S3/File storage"
    }

    cbr = softwareSystem "CBR" "RUONIA, key rate, repo, reserves."
    minfin = softwareSystem "MinFin" "OFZ auctions."
    nalog = softwareSystem "FTS" "Tax calendar."
    roskazna = softwareSystem "Treasury" "Deposits and EKS placements."

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
    }

    container psbSystem "Containers" {
      include *
    }

    component backend "GoBackendComponents" {
      include *
    }

    component mlService "PythonMLComponents" {
      include *
    }

    styles {
      element "Element" {
        fontSize 20
      }

      element "Person" {
        shape person
        background "#0B5CAD"
        color "#FFFFFF"
        width 300
        height 160
        metadata false
      }

      element "Software System" {
        background "#0B5CAD"
        color "#FFFFFF"
        width 330
        height 180
        metadata false
      }

      element "Container" {
        background "#FFFFFF"
        color "#000000"
        stroke "#0B5CAD"
        width 300
        height 160
        metadata false
      }

      element "Database" {
        shape cylinder
        background "#FFF7ED"
        color "#000000"
        stroke "#F97316"
        width 270
        height 145
        metadata false
      }

      element "Component" {
        background "#FFFFFF"
        color "#000000"
        stroke "#F97316"
        width 250
        height 135
        metadata false
      }

      relationship "Relationship" {
        fontSize 16
        width 140
      }
    }
  }
}
