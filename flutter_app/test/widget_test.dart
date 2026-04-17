import 'package:exif_editor_flutter/main.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('App shell renders status panel', (WidgetTester tester) async {
    await tester.pumpWidget(const ExifEditorApp());
    await tester.pumpAndSettle();

    expect(find.text('Control Center'), findsOneWidget);
  });
}
