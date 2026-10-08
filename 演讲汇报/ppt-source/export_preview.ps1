$ErrorActionPreference = 'Stop'
$pp = New-Object -ComObject PowerPoint.Application
$outDir = 'D:\tmp\meow-ppt'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$files = @(
  'D:\Project\JXprojiect\Hermes-project\project\yixiaomiao-medqa\演讲汇报\汇报PPT_医疗专家微调.pptx'
)
$i = 0
foreach ($f in $files) {
  $i++
  $pres = $pp.Presentations.Open($f, $true, $false, $false)
  $n = $pres.Slides.Count
  foreach ($j in 1..$n) {
    $out = Join-Path $outDir ("deck{0}-slide{1:D2}.png" -f $i, $j)
    $pres.Slides.Item($j).Export($out, 'PNG', 1600, 900)
  }
  $pres.Close()
  Write-Output ("deck{0}: {1} slides exported" -f $i, $n)
}
$pp.Quit()
Write-Output "ALL DONE"
