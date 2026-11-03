import '../lib/models/grid_forecast.dart';
import '../lib/services/grid_api_client.dart';

void main() async {
  print('--- Dart Client Initiating HTTP Request to Flask PyTorch Backend ---');
  final client = GridApiClient(baseUrl: 'http://127.0.0.1:5050');

  try {
    final req = ForecastRequest(
      sectorName: 'Metro-Downtown',
      hour: 16,
      dayOfWeek: 3,
      tempC: 37.5, // High temperature drive AC load
      solarWm2: 890.0,
      industrialIdx: 0.92,
    );

    print('  [HTTP POST] /api/v1/forecast with Payload:');
    print('    Sector: ${req.sectorName} | Hour: ${req.hour} | Temp: ${req.tempC}C | Solar: ${req.solarWm2} W/m2');

    final response = await client.requestForecast(req);

    print('  [HTTP 200 OK] Response Received & Deserialized:');
    print('    SQL Record ID:      ${response.recordId}');
    print('    AI Predicted Load:  ${response.predictedLoadMw} MW');
    print('    Dispatch Strategy:  ${response.dispatchDecision}');
    print('    Spinning Reserve:   ${response.spinningReserveTargetMw} MW');
    print('    Server Timestamp:   ${response.createdAt}');

    print('\nDART CLIENT HTTP FULL-STACK ROUNDTRIP VERIFIED SUCCESSFULLY.');
  } finally {
    client.close();
  }
}
