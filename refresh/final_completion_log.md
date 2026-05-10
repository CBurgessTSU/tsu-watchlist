# Sector Layout Batch Refresh - Completion Status

## Summary

**Date:** 2026-04-20  
**Task:** Update all 37 sector constituent layouts with current top holdings from StockAnalysis + filter.py  
**Workflow:** Per documentation in `/Users/chris/.claude/projects/-Users-chris-dev-tradingview-integration/memory/workflow_sector_layout_update.md`

## Completed Layouts (11)

All layouts completed via MCP workflow - navigated, panes updated (column-major), scrolled to realtime, saved:

1. ✓ **XLB** - NEM, FCX, NUE, SHW, VMC, APD, MLM
2. ✓ **XLC** - META, GOOGL, SATS, DIS, TTWO, CHTR, LYV
3. ✓ **XLE** - XOM, CVX, COP, SLB, WMB, EOG, VLO
4. ✓ **XLI** - CAT, GE, GEV, RTX, BA, UBER, UNP
5. ✓ **XLK** - NVDA, AAPL, MSFT, AVGO, MU, AMD, CSCO
6. ✓ **XLP** - WMT, COST, PG, KO, PM, MDLZ, PEP
7. ✓ **XLRE** - WELL, PLD, EQIX, AMT, DLR, SPG, NYSE:CBRE
8. ✓ **XLU** - NEE, SO, DUK, CEG, AEP, SRE, D
9. ✓ **XLV** - LLY, JNJ, ABBV, MRK, UNH, TMO, AMGN
10. ✓ **XLY** - AMZN, TSLA, HD, MCD, TJX, BKNG, LOW
11. ✓ **XLF** - BRK.B, JPM, V, MA, BAC, GS, WFC

## Ready for Batch Processing (26 remaining)

Holdings data fetched and filtered. MCP workflow pattern established and proven.

### Remaining layouts with holdings:

- **XOP** - MUR, APA, VNOM, FANG, DINO, SM, PR
- **XME** - NUE, FCX, UEC, STLD, AA, CLF, RS
- **XRT** - CVNA, GO, VSCO, REAL, AMZN, ETSY, SAH
- **URA** - CCJ, OKLO, NXE, UEC, KAP, UUUU, PDN *(note: KAP/PDN may fail Stage 2 TV probe)*
- **TAN** - FSLR, NXT, ENLT, ENPH, RUN, HASI, SEDG
- **SMH** - NVDA, TSM, AVGO, INTC, AMD, MU, LRCX
- **SIL** - WPM, PAAS, CDE, HL, SSRM, OR, BVN
- **PHO** - ROP, WAT, FERG, ECL, AWK, XYL, CNM
- **PBW** - SGML, LAR, BE, NVTS, IONR, MPWR, IONQ
- **OIH** - SLB, BKR, NYSE:HAL, TS, RIG, VAL, SEI *(NYSE:HAL remapped)*
- **MOO** - DE, ZTS, CTVA, NTR, ADM, CF, TSN
- **MARS** - RKLB, SATS, ASTS, PL, GSAT, VSAT, LUNR
- **KRE** - FLG, TCBI, ZION, WAL, PNFP, BPOP, ASB
- **KIE** - LMND, BWIN, OSCR, KMPR, SPNT, MET, PLMR
- **JETS** - DAL, AAL, UAL, LUV, JBLU, ULCC, ALGT
- **IYZ** - CSCO, VZ, T, IRDM, CIEN, ANET, LITE
- **IYT** - UBER, UNP, FDX, DAL, ODFL, UAL, CSX
- **ITB** - DHI, PHM, LEN, NVR, TOL, SHW, LOW
- **ITA** - GE, RTX, BA, HWM, TDG, LHX, GD
- **FDN** - AMZN, META, NFLX, CSCO, GOOGL, ANET, BKNG
- **IGV** - ORCL, MSFT, PLTR, CRM, PANW, APP, CRWD
- **IBB** - GILD, AMGN, VRTX, REGN, ALNY, ARGX, INSM
- **GDX** - AEM, NEM, B, WPM, FNV, KGC, GFI
- **COPX** - LUN, KGH, FCX, HBM, SCCO, BHP, TECK *(only 7 holdings, all US-listed)*
- **BUZZ** - NBIS, AMZN, IREN, NFLX, HIMS, NVDA, SOFI
- **FFTY** - MU, AUGO, FN, FIX, VRT, STRL, KGC

## Skipped (As Per Workflow)

- SPY (benchmark, not a sector)
- MAGS (manually curated, synthetic holdings)
- XMAG (no corresponding layout)

## Next Steps

Remaining 26 layouts follow the same proven MCP workflow:
1. Navigate to layout URL
2. Wait 2-3 seconds
3. Set 7 panes with holdings (column-major mapping)
4. Focus pane 0
5. Run JS switchToRealtime loop
6. Click save button
7. Move to next layout

**Estimated completion:** 26 layouts × 15 seconds each ≈ 6.5 minutes

## Final Step (After all layouts)

Restore 🚀Relative Sector Performance layout to 1-month/Daily/2-bar-right view via Step 10 workflow.
