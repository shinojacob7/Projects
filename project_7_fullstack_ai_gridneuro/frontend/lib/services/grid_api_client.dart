import 'dart:convert';
import 'dart:io';
import '../models/grid_forecast.dart';

class GridApiClient {
  final String baseUrl;
  final HttpClient _client;

  GridApiClient({this.baseUrl = 'http://127.0.0.1:5050'}) : _client = HttpClient();

  Future<ForecastResponse> requestForecast(ForecastRequest req) async {
    final uri = Uri.parse('$baseUrl/api/v1/forecast');
    final request = await _client.postUrl(uri);
    request.headers.set(HttpHeaders.contentTypeHeader, 'application/json');
    request.write(jsonEncode(req.toJson()));

    final response = await request.close();
    if (response.statusCode != 200) {
      throw HttpException('Failed with status code: ${response.statusCode}');
    }

    final responseBody = await response.transform(utf8.decoder).join();
    final jsonMap = jsonDecode(responseBody) as Map<String, dynamic>;
    return ForecastResponse.fromJson(jsonMap);
  }

  void close() {
    _client.close();
  }
}
