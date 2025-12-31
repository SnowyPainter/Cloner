using System;
using System.Collections.Generic;
using System.Text;

namespace Cloner.Models
{
    public class SubtitleOption
    {
        // CLI에 넘길 실제 값
        public string LangCode { get; set; } = "";

        // UI에 보여줄 이름
        public string DisplayName { get; set; } = "";
    }
}
