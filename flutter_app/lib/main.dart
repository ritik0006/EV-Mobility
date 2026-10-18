import 'package:flutter/material.dart';
import 'api.dart';
import 'home_screen.dart';
import 'login_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Api.load();
  runApp(const App());
}

class App extends StatelessWidget {
  const App({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'EV Rent',
        theme: ThemeData(colorSchemeSeed: Colors.green, useMaterial3: true),
        home: Api.token == null ? const LoginScreen() : const HomeScreen(),
      );
}
