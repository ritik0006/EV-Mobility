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
        builder: (context, child) => Container(
          color: const Color(0xFFEDF7F1),
          alignment: Alignment.topCenter,
          child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 520), child: child),
        ),
        home: Api.token == null ? const LoginScreen() : const HomeScreen(),
      );
}
