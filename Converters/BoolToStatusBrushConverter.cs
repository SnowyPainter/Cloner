using System;
using System.Globalization;
using System.Windows.Data;
using System.Windows.Media;

namespace Cloner.Converters
{
    public class BoolToStatusBrushConverter : IValueConverter
    {
        // true  → built (green)
        // false → not built (gray)
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            if (value is bool isBuilt)
            {
                return isBuilt
                    ? new SolidColorBrush(Color.FromRgb(34, 197, 94))   // green-500
                    : new SolidColorBrush(Color.FromRgb(148, 163, 184)); // slate-400
            }

            return new SolidColorBrush(Color.FromRgb(148, 163, 184));
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            throw new NotSupportedException();
        }
    }
}
