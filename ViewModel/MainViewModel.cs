using Cloner.Models;
using Cloner.Services;
using System;
using System.Collections.ObjectModel;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Input;

namespace Cloner.ViewModel
{
    public class MainViewModel : ViewModelBase
    {
        private readonly PythonCliService _cli;
        private readonly string _workspacePath;

        public MainViewModel()
        {
            _cli = new PythonCliService();
            _workspacePath = Path.Combine(
                AppDomain.CurrentDomain.BaseDirectory,
                "workspace"
            );

            // === CLI 로그 ===
            _cli.OnRawLog += AppendLog;

            // === Translate options ===
            AvailableTranslateLangs = new ObservableCollection<string>
            {
                "ko", "ja", "zh"
            };
            SelectedTranslateLang = "ko";

            Assets = new ObservableCollection<AssetViewModel>();

            // === Commands ===
            IngestCommand = new RelayCommand(
                async _ => await RunIngestAsync(),
                _ => !IsProcessing && !string.IsNullOrWhiteSpace(YoutubeUrl)
            );

            BuildCommand = new RelayCommand(
                async _ => await RunBuildAsync(),
                _ => !IsProcessing && SelectedAsset != null
            );

            DeleteAssetCommand = new RelayCommand(
                _ => DeleteSelectedAsset(),
                _ => !IsProcessing && SelectedAsset != null
            );


            SelectAssetCommand = new RelayCommand(
                asset => SelectAsset(asset as AssetViewModel)
            );

            AppendLog("Application started.");
            RefreshAssets();
        }

        // =========================================================
        // Properties
        // =========================================================

        private string _youtubeUrl = "";
        public string YoutubeUrl
        {
            get => _youtubeUrl;
            set
            {
                _youtubeUrl = value;
                OnPropertyChanged();
                RaiseCommands();
            }
        }

        private string _consoleLogs = "";
        public string ConsoleLogs
        {
            get => _consoleLogs;
            set { _consoleLogs = value; OnPropertyChanged(); }
        }

        private bool _isProcessing;
        public bool IsProcessing
        {
            get => _isProcessing;
            set
            {
                _isProcessing = value;
                OnPropertyChanged();
                RaiseCommands();
            }
        }

        // === Ingest translate ===
        public ObservableCollection<string> AvailableTranslateLangs { get; }

        private string _selectedTranslateLang = "ko";
        public string SelectedTranslateLang
        {
            get => _selectedTranslateLang;
            set { _selectedTranslateLang = value; OnPropertyChanged(); }
        }

        // === Build text ===
        private string _buildTitle = "";
        public string BuildTitle
        {
            get => _buildTitle;
            set { _buildTitle = value; OnPropertyChanged(); }
        }

        private string _buildTagline = "";
        public string BuildTagline
        {
            get => _buildTagline;
            set { _buildTagline = value; OnPropertyChanged(); }
        }

        private string _watermark = ""; 
        public string Watermark
        {
            get => _watermark;
            set { _watermark = value; OnPropertyChanged(); }
        }

        private string _buildCountText = "1";
        public string BuildCountText
        {
            get => _buildCountText;
            set { _buildCountText = value; OnPropertyChanged(); }
        }

        // === Assets ===
        public ObservableCollection<AssetViewModel> Assets { get; }

        private AssetViewModel? _selectedAsset;
        public AssetViewModel? SelectedAsset
        {
            get => _selectedAsset;
            set
            {
                _selectedAsset = value;
                OnPropertyChanged();
                RaiseCommands();
            }
        }

        // Build panel bindings
        public ObservableCollection<SubtitleOption>? AvailableSrts =>
            SelectedAsset?.AvailableSrts;

        public SubtitleOption? SelectedSrt
        {
            get => SelectedAsset?.SelectedSrt;
            set
            {
                if (SelectedAsset != null)
                {
                    SelectedAsset.SelectedSrt = value;
                    OnPropertyChanged();
                    RaiseCommands();
                }
            }
        }

        // =========================================================
        // Commands
        // =========================================================

        public ICommand IngestCommand { get; }
        public ICommand BuildCommand { get; }
        public ICommand DeleteAssetCommand { get; }
        public ICommand SelectAssetCommand { get; }

        // =========================================================
        // Logic
        // =========================================================

        private async Task RunIngestAsync()
        {
            IsProcessing = true;
            AppendLog("[INGEST] start");

            Directory.CreateDirectory(_workspacePath);

            string args =
                $"-m reels.cli.main ingest {YoutubeUrl} " +
                $"--translate {SelectedTranslateLang}";

            await _cli.RunAsync(args);

            RefreshAssets();

            AppendLog("[INGEST] complete");
            IsProcessing = false;
        }

        private async Task RunBuildAsync()
        {
            IsProcessing = true;
            AppendLog($"[BUILD] {SelectedAsset.AssetId}");

            var argsList = new List<string>
            {
                "-m reels.cli.main build",
                SelectedAsset.AssetId
            };

            // SRT (선택)
            if (SelectedAsset.SelectedSrt != null)
            {
                argsList.Add($"--translated-lang {SelectedAsset.SelectedSrt.LangCode}");
            }

            // Title (선택)
            if (!string.IsNullOrWhiteSpace(BuildTitle))
            {
                argsList.Add($"--title \"{BuildTitle}\"");
            }

            // Tagline (선택)
            if (!string.IsNullOrWhiteSpace(BuildTagline))
            {
                argsList.Add($"--tagline \"{BuildTagline}\"");
            }

            // Watermark (선택)
            if (!string.IsNullOrWhiteSpace(Watermark))
            {
                argsList.Add($"--watermark \"{Watermark}\"");
            }

            if (int.TryParse(BuildCountText, out int count) && count > 1)
            {
                argsList.Add($"--count {count}");
            }

            string args = string.Join(" ", argsList);


            await _cli.RunAsync(args);

            var output = Path.Combine(
                SelectedAsset.FolderPath,
                "output",
                "reel_60s.mp4"
            );

            if (File.Exists(output))
            {
                SelectedAsset.IsBuilt = true;
                SelectedAsset.OutputPath = output;
                AppendLog($"[SUCCESS] {output}");

                var outputDir = Path.GetDirectoryName(output);
                if (outputDir != null && Directory.Exists(outputDir))
                {
                    Process.Start(new ProcessStartInfo
                    {
                        FileName = "explorer.exe",
                        Arguments = outputDir,
                        UseShellExecute = true
                    });
                }
            }

            IsProcessing = false;
        }

        private void RefreshAssets()
        {
            Assets.Clear();

            var assetsDir = Path.Combine(_workspacePath, "assets");
            if (!Directory.Exists(assetsDir))
                return;

            foreach (var dir in Directory.GetDirectories(assetsDir))
            {
                var assetVm = new AssetViewModel
                {
                    AssetId = Path.GetFileName(dir),
                    FolderPath = dir
                };
                assetVm.LoadMetadata();
                Assets.Add(assetVm);
            }
        }

        private void SelectAsset(AssetViewModel? asset)
        {
            if (asset == null)
                return;

            foreach (var a in Assets)
                a.IsSelected = false;

            asset.IsSelected = true;
            asset.LoadSrts();

            SelectedAsset = asset;

            OnPropertyChanged(nameof(AvailableSrts));
            OnPropertyChanged(nameof(SelectedSrt));
        }

        private void DeleteSelectedAsset()
        {
            if (SelectedAsset == null)
                return;

            var confirm = MessageBox.Show(
                $"Delete asset \"{SelectedAsset.AssetId}\"?\nThis removes asset and all its data.",
                "Delete Asset",
                MessageBoxButton.YesNo,
                MessageBoxImage.Warning
            );

            if (confirm != MessageBoxResult.Yes)
                return;

            var assetsRoot = Path.GetFullPath(Path.Combine(_workspacePath, "assets"));
            var assetFolder = Path.GetFullPath(SelectedAsset.FolderPath);

            if (!assetFolder.StartsWith(assetsRoot, StringComparison.OrdinalIgnoreCase))
            {
                MessageBox.Show("Invalid asset path.");
                return;
            }

            try
            {
                RemoveFromRegistry(SelectedAsset.AssetId);

                if (Directory.Exists(assetFolder))
                    Directory.Delete(assetFolder, true);

                Assets.Remove(SelectedAsset);
                SelectedAsset = null;
                OnPropertyChanged(nameof(AvailableSrts));
                OnPropertyChanged(nameof(SelectedSrt));

                AppendLog($"[DELETE] {assetFolder}");
            }
            catch (Exception ex)
            {
                Debug.WriteLine(ex.Message);
                MessageBox.Show($"Failed to delete asset: {ex.Message}");
            }
        }

        private void RemoveFromRegistry(string assetId)
        {
            var registryPath = Path.Combine(_workspacePath, "assets", "registry.json");
            if (!File.Exists(registryPath))
                return;

            try
            {
                var json = File.ReadAllText(registryPath);
                if (string.IsNullOrWhiteSpace(json))
                    return;

                var data = JsonSerializer.Deserialize<Dictionary<string, string>>(json);
                if (data == null || data.Count == 0)
                    return;

                var keysToRemove = data
                    .Where(kv => string.Equals(kv.Key, assetId, StringComparison.OrdinalIgnoreCase)
                        || string.Equals(kv.Value, assetId, StringComparison.OrdinalIgnoreCase))
                    .Select(kv => kv.Key)
                    .ToList();

                if (keysToRemove.Count == 0)
                    return;

                foreach (var key in keysToRemove)
                    data.Remove(key);

                var updated = JsonSerializer.Serialize(
                    data,
                    new JsonSerializerOptions { WriteIndented = false }
                );
                File.WriteAllText(registryPath, updated);
            }
            catch (Exception ex)
            {
                Debug.WriteLine(ex.Message);
            }
        }

        // =========================================================
        // Helpers
        // =========================================================

        private void AppendLog(string text)
        {
            ConsoleLogs += text + Environment.NewLine;
        }

        private void RaiseCommands()
        {
            (IngestCommand as RelayCommand)?.RaiseCanExecuteChanged();
            (BuildCommand as RelayCommand)?.RaiseCanExecuteChanged();
            (DeleteAssetCommand as RelayCommand)?.RaiseCanExecuteChanged();
        }
    }
}
