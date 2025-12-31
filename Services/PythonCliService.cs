using Cloner.Models;
using System;
using System.Diagnostics;
using System.IO;
using System.Threading.Tasks;

namespace Cloner.Services
{
    public class PythonCliService
    {
        private readonly string _appRoot;
        private readonly string _pythonExe;

        public event Action<CliEvent>? OnEvent;
        public event Action<string>? OnRawLog; // stderr or 파싱 실패

        public PythonCliService()
        {
            _appRoot = AppContext.BaseDirectory;
            _pythonExe = Path.Combine(_appRoot, "python", "python.exe");
        }

        public async Task RunAsync(string args)
        {
            var psi = new ProcessStartInfo
            {
                FileName = _pythonExe,
                Arguments = args,
                WorkingDirectory = _appRoot,
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true
            };

            psi.Environment["HF_HOME"] = "cache\\hf";
            psi.Environment["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1";

            using var process = new Process { StartInfo = psi };

            process.OutputDataReceived += (_, e) =>
            {
                if (string.IsNullOrWhiteSpace(e.Data)) return;

                try
                {
                    var evt = CliEventParser.Parse(e.Data);
                    OnEvent?.Invoke(evt);
                }
                catch (Exception ex)
                {
                    OnRawLog?.Invoke($"[PARSE_ERROR] {ex.Message}\n{e.Data}");
                }
            };

            process.ErrorDataReceived += (_, e) =>
            {
                if (!string.IsNullOrWhiteSpace(e.Data))
                    OnRawLog?.Invoke(e.Data);
            };

            process.Start();
            process.BeginOutputReadLine();
            process.BeginErrorReadLine();

            await process.WaitForExitAsync();
        }
    }
}
