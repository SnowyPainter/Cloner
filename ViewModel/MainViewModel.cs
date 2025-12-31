using Cloner.Models;
using Cloner.Services;
using System;
using System.Collections.ObjectModel;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
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
                _ => !IsProcessing
                     && SelectedAsset != null
                     && SelectedAsset.SelectedSrt != null
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
            IsProcessing = false;
        }

        private async Task RunBuildAsync()
        {
            if (SelectedAsset?.SelectedSrt == null)
                return;

            IsProcessing = true;
            AppendLog($"[BUILD] {SelectedAsset.AssetId} ({SelectedAsset.SelectedSrt.LangCode})");

            string args =
                $"-m reels.cli.main build {SelectedAsset.AssetId} " +
                $"--translated-lang {SelectedAsset.SelectedSrt.LangCode} " +
                $"--title \"{BuildTitle}\" " +
                $"--tagline \"{BuildTagline}\" " +
                $"--watermark \"{Watermark}\"";

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
        }
    }
}
