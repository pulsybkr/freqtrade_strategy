freqtrade backtesting --config ./user_data/spot_config.json --strategy-list "NASOSv4" \
"NASOSv5HO" "NASOSv5PD" "NASOSv5SL" "NASOSv5_mod3" "NFI5MOHO_WIP" "Obelisk_Ichimoku_ZEMA_v1" \
"SMAOffsetProtectOptV1" "SampleStrategy" "SmaRsiHopt" "TrailingBuyStrat" "slope_is_dope2" --timeframe 5m \
--timerange=$(date -d '60 days ago' +%Y%m%d)-$(date +%Y%m%d)

freqtrade backtesting --config ./user_data/spot_config.json --strategy "IchimokuHaulingV8a" --timeframe 5m 

freqtrade trade --config ./user_data/m_config.json --strategy "MacheteV8b" --timeframe 15m