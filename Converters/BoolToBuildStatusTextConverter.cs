using System;
using System.Globalization;
using System.Windows.Data;

namespace Cloner.Converters
{
    public class BoolToBuildStatusTextConverter : IValueConverter
    {
        // true  -> Built
        // false -> Not Built
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            if (value is bool isBuilt)
            {
                return isBuilt ? "Built" : "Not Built";
            }

            return "Unknown";
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            throw new NotSupportedException();
        }
    }
}
