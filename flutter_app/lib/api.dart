import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class Api {
  // Android emulator -> your PC. On a real phone use your PC's LAN IP or the deployed server URL.
  static const base = 'http://10.0.2.2:8000/api';
  static String? token;
  static String? role;

  static Future<void> load() async {
    final p = await SharedPreferences.getInstance();
    token = p.getString('token');
    role = p.getString('role');
  }

  static Future<void> saveSession(Map d) async {
    token = d['token'];
    role = d['role'];
    final p = await SharedPreferences.getInstance();
    await p.setString('token', token!);
    await p.setString('role', role!);
  }

  static Future<void> logout() async {
    token = null;
    role = null;
    (await SharedPreferences.getInstance()).clear();
  }

  static Map<String, String> get _auth => {if (token != null) 'Authorization': 'Token $token'};

  static Future<dynamic> get(String path) async =>
      _out(await http.get(Uri.parse('$base$path'), headers: _auth));

  static Future<dynamic> post(String path, Map body) async => _out(await http.post(
      Uri.parse('$base$path'),
      headers: {..._auth, 'Content-Type': 'application/json'},
      body: jsonEncode(body)));

  /// Multipart upload: [files] maps field name -> local file path.
  static Future<dynamic> upload(String path, Map<String, String> fields, Map<String, String> files) async {
    final req = http.MultipartRequest('POST', Uri.parse('$base$path'))..headers.addAll(_auth);
    req.fields.addAll(fields);
    for (final e in files.entries) {
      req.files.add(await http.MultipartFile.fromPath(e.key, e.value));
    }
    return _out(await http.Response.fromStream(await req.send()));
  }

  static dynamic _out(http.Response r) {
    final d = r.body.isEmpty ? null : jsonDecode(r.body);
    if (r.statusCode >= 400) {
      final msg = d is Map ? (d['detail'] ?? d.values.first) : 'Error ${r.statusCode}';
      throw Exception(msg is List ? msg.first : msg);
    }
    return d;
  }
}

void toast(BuildContext c, String m) =>
    ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(m.replaceFirst('Exception: ', ''))));
