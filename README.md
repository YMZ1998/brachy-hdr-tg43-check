# brachy-hdr-tg43-check

Purpose
----------------------
A command line interface to independently calculate doses from brachytherapy RTPlan files. For research purposes only.

Install
-------
```
pip install -r requirements.txt
```

Usage
-------
```
python main.py
```
Start the program, then输入本地 RTPLAN DICOM 文件路径（可输入 `quit` 退出）。程序会读取该计划并输出 TG43 复核结果。

Parser
-----
The RTPLAN file is parsed by `hdrpackage\parse_omp_rtplan.py`.

TG43
-----
The [TG43](https://www.google.co.uk/url?sa=t&rct=j&q=&esrc=s&source=web&cd=1&ved=0ahUKEwjPvfn54PvRAhUKsBQKHQmZAPQQFggcMAA&url=http%3A%2F%2Fwww.teambest.com%2Fbesttotalsolutions%2FPDFs%2FTG43_update_Iodine_Rivard_Coursey_DeWerd_et_al_March2004.pdf&usg=AFQjCNE9doofriCa-TNFCPn6YEvWB4xBQg&sig2=7Tpv3NUcPVXjMRY1jhXGhw) brachytherapy dose calculation method is included here for use with a MicroSelectron 192Ir source. Raw source data files have been transcribed from the [ESTRO consensus dataset](http://www.estro.org/about/governance-organisation/committees-activities/tg43-ir-192-hdr) in the `hdrpackage\source_files` directory.

Tests
-----
Run tests with:
```
python -m pytest -q
```
