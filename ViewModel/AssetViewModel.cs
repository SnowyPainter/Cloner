using Cloner.Models;
using System.Collections.ObjectModel;
using System.Diagnostics;
using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Input;

namespace Cloner.ViewModel
{
    public class AssetViewModel : ViewModelBase
    {
        // === 기본 식별자 ===

        private AssetMetadata? _metadata;
        public AssetMetadata? Metadata
        {
            get => _metadata;
            set { _metadata = value; OnPropertyChanged(); }
        }


        private string _assetId = "";
        public string AssetId
        {
            get => _assetId;
            set { _assetId = value; OnPropertyChanged(); }
        }

        private string _folderPath = "";
        public string FolderPath
        {
            get => _folderPath;
            set { _folderPath = value; OnPropertyChanged(); }
        }

        // === UI 선택 상태 ===
        private bool _isSelected;
        public bool IsSelected
        {
            get => _isSelected;
            set { _isSelected = value; OnPropertyChanged(); }
        }

        // === Draft translated subtitles (lang-based) ===
        private ObservableCollection<SubtitleOption> _availableSrts = new();
        public ObservableCollection<SubtitleOption> AvailableSrts
        {
            get => _availableSrts;
            set { _availableSrts = value; OnPropertyChanged(); }
        }

        private SubtitleOption? _selectedSrt;
        public SubtitleOption? SelectedSrt
        {
            get => _selectedSrt;
            set { _selectedSrt = value; OnPropertyChanged(); }
        }

        // === 빌드 결과 ===
        private bool _isBuilt;
        public bool IsBuilt
        {
            get => _isBuilt;
            set { _isBuilt = value; OnPropertyChanged(); }
        }

        private string? _outputPath;
        public string? OutputPath
        {
            get => _outputPath;
            set { _outputPath = value; OnPropertyChanged(); }
        }

        public string Title => Metadata?.Title ?? "—";

        public string Source => Metadata?.Source ?? "—";

        public string DurationText =>
            Metadata != null ? $"{Metadata.Duration:0.0}s" : "—";

        public string CreatedAtText =>
            Metadata != null ? Metadata.CreatedAt.ToLocalTime().ToString("yyyy-MM-dd HH:mm") : "—";
        public ICommand OpenOutputCommand => new RelayCommand(ExecuteOpenOutput);
        public ICommand CopyMetadata => new RelayCommand(ExecuteCopyMetadata);

        private void ExecuteCopyMetadata(object? parameter)
        {
            if (Metadata == null)
            {
                MessageBox.Show("There's no metadata");
                return;
            }

            try
            {
                string subtitleSummary = "자막 없음";
                var srtPath = Path.Combine(
                        FolderPath,
                        "subtitles",
                        $"original.srt"
                    );
                
                 if (File.Exists(srtPath)) subtitleSummary = LoadSrtPlainText(srtPath);
                

                var prompt = $"""
[콘텐츠 정보]
- 영화 제목: {Metadata.Title}

[자막 기반 장면 요약]
{subtitleSummary}

[AI 영상 프롬프트 (영문)]
A cinematic movie scene based on the dialogue above,
emotional tension, dramatic atmosphere, expressive characters.

[요청]
위 프롬프트를 참고해서 한국어로 릴스용 설명 문구를 만들어줘.
""";

                Clipboard.SetText(prompt);
                MessageBox.Show("AI Prompt just copied");
            }
            catch (Exception ex)
            {
                Debug.WriteLine(ex.Message);
                MessageBox.Show("Failed to create prompts");
            }
        }


        private void ExecuteOpenOutput(object? parameter)
        {
            if (string.IsNullOrEmpty(this.FolderPath))
            {
                MessageBox.Show("폴더 경로가 설정되지 않았습니다.");
                return;
            }

            string outputDir = Path.Combine(this.FolderPath, "output");

            try
            {
                if (!Directory.Exists(outputDir))
                {
                    // output 폴더 자체가 없으면 그냥 상위 폴더 열기
                    Process.Start(new ProcessStartInfo { FileName = this.FolderPath, UseShellExecute = true });
                    return;
                }

                // 1. output 폴더 내의 reel_ 로 시작하는 모든 파일 가져오기
                var directoryInfo = new DirectoryInfo(outputDir);
                var latestFile = directoryInfo.GetFiles("reel_*.*")
                    // 2. 비디오 확장자만 필터링 (선택 사항)
                    .Where(f => f.Extension.Equals(".mp4", StringComparison.OrdinalIgnoreCase) ||
                                f.Extension.Equals(".mov", StringComparison.OrdinalIgnoreCase) ||
                                f.Extension.Equals(".mkv", StringComparison.OrdinalIgnoreCase))
                    // 3. 생성 시간(CreationTime) 기준으로 내림차순 정렬
                    .OrderByDescending(f => f.CreationTime)
                    // 4. 가장 최신 파일 하나 선택
                    .FirstOrDefault();

                if (latestFile != null)
                {
                    // 최신 비디오 파일 실행 (시스템 기본 플레이어)
                    Process.Start(new ProcessStartInfo
                    {
                        FileName = latestFile.FullName,
                        UseShellExecute = true
                    });
                }
                else
                {
                    // 파일이 없으면 폴더라도 열어줌
                    Process.Start(new ProcessStartInfo { FileName = outputDir, UseShellExecute = true });
                }
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"파일 실행 실패: {ex.Message}");
                MessageBox.Show($"파일을 실행할 수 없습니다: {ex.Message}");
            }
        }
        // === 헬퍼 ===

        public void RefreshBuildStatus()
        {
            if (!Directory.Exists(FolderPath)) return;

            // reel_ 로 시작하는 첫 번째 파일 검색
            var buildFile = Directory.GetFiles(Path.Combine(FolderPath, "output"), "reel_*.*")
                                     .FirstOrDefault();

            if (buildFile != null)
            {
                IsBuilt = true;
                OutputPath = buildFile;
            }
            else
            {
                IsBuilt = false;
                OutputPath = null;
            }
        }

        public void LoadSrts()
        {
            AvailableSrts.Clear();
            SelectedSrt = null;

            var srtDir = Path.Combine(FolderPath, "subtitles");
            if (!Directory.Exists(srtDir))
                return;

            foreach (var file in Directory.GetFiles(srtDir, "translated_*.srt"))
            {
                // translated_ko.srt → ko
                var lang = Path.GetFileNameWithoutExtension(file)
                    .Replace("translated_", "")
                    .ToLowerInvariant();

                AvailableSrts.Add(new SubtitleOption
                {
                    LangCode = lang,
                    DisplayName = $"Draft translated subtitle ({lang.ToUpperInvariant()})"
                });
            }
        }

        public void LoadMetadata()
        {
            var path = Path.Combine(FolderPath, "asset.json");
            if (!File.Exists(path))
            {
                Metadata = null;
                return;
            }

            try
            {
                var json = File.ReadAllText(path);
                Metadata = JsonSerializer.Deserialize<AssetMetadata>(
                    json,
                    new JsonSerializerOptions
                    {
                        PropertyNameCaseInsensitive = true
                    });

                // asset_id는 metadata 기준으로 동기화
                if (!string.IsNullOrWhiteSpace(Metadata?.AssetId))
                    AssetId = Metadata.AssetId;
                RefreshBuildStatus();
                // 파생 프로퍼티 갱신
                OnPropertyChanged(nameof(Title));
                OnPropertyChanged(nameof(Source));
                OnPropertyChanged(nameof(DurationText));
                OnPropertyChanged(nameof(CreatedAtText));
            }
            catch
            {
                // JSON 깨졌을 때 앱 터지면 안 됨
                Metadata = null;
            }
        }

        private string LoadSrtPlainText(string srtPath, int maxChars = 800)
        {
            var lines = File.ReadAllLines(srtPath);
            var textLines = lines
                .Where(l => !string.IsNullOrWhiteSpace(l))
                .Where(l => !l.Contains("-->"))
                .Where(l => !int.TryParse(l, out _))
                .ToList();

            var joined = string.Join(" ", textLines);

            return joined.Length > maxChars
                ? joined.Substring(0, maxChars) + "..."
                : joined;
        }


    }
}
