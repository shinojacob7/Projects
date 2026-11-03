class ForecastRequest {
  final String sectorName;
  final int hour;
  final int dayOfWeek;
  final double tempC;
  final double solarWm2;
  final double industrialIdx;

  ForecastRequest({
    required this.sectorName,
    required this.hour,
    required this.dayOfWeek,
    required this.tempC,
    required this.solarWm2,
    required this.industrialIdx,
  });

  Map<String, dynamic> toJson() => {
    'sector_name': sectorName,
    'hour': hour,
    'day_of_week': dayOfWeek,
    'temp_c': tempC,
    'solar_wm2': solarWm2,
    'industrial_idx': industrialIdx,
  };
}

class ForecastResponse {
  final int recordId;
  final String sectorName;
  final double predictedLoadMw;
  final String dispatchDecision;
  final double spinningReserveTargetMw;
  final String createdAt;

  ForecastResponse({
    required this.recordId,
    required this.sectorName,
    required this.predictedLoadMw,
    required this.dispatchDecision,
    required this.spinningReserveTargetMw,
    required this.createdAt,
  });

  factory ForecastResponse.fromJson(Map<String, dynamic> json) {
    return ForecastResponse(
      recordId: json['record_id'] as int,
      sectorName: json['sector_name'] as String,
      predictedLoadMw: (json['predicted_load_mw'] as num).toDouble(),
      dispatchDecision: json['dispatch_decision'] as String,
      spinningReserveTargetMw: (json['spinning_reserve_target_mw'] as num).toDouble(),
      createdAt: json['created_at'] as String,
    );
  }
}
