import 'package:test/test.dart';
import '../lib/models/grid_forecast.dart';

void main() {
  group('GridNeuro Frontend Client Unit Tests', () {
    test('ForecastRequest to JSON serialization', () {
      final req = ForecastRequest(
        sectorName: 'Metro-Downtown',
        hour: 14,
        dayOfWeek: 2,
        tempC: 32.5,
        solarWm2: 840.0,
        industrialIdx: 0.95,
      );

      final json = req.toJson();
      expect(json['sector_name'], equals('Metro-Downtown'));
      expect(json['hour'], equals(14));
      expect(json['temp_c'], equals(32.5));
      expect(json['industrial_idx'], equals(0.95));
    });

    test('ForecastResponse from JSON deserialization', () {
      final raw = {
        'record_id': 101,
        'sector_name': 'Metro-Downtown',
        'predicted_load_mw': 582.45,
        'dispatch_decision': 'RAMP_PEAKER_PLANTS_AND_BATTERY_DISCHARGE',
        'spinning_reserve_target_mw': 87.37,
        'created_at': '2026-11-03T19:30:00Z',
      };

      final response = ForecastResponse.fromJson(raw);
      expect(response.recordId, equals(101));
      expect(response.sectorName, equals('Metro-Downtown'));
      expect(response.predictedLoadMw, equals(582.45));
      expect(response.dispatchDecision, equals('RAMP_PEAKER_PLANTS_AND_BATTERY_DISCHARGE'));
      expect(response.spinningReserveTargetMw, equals(87.37));
    });
  });
}
