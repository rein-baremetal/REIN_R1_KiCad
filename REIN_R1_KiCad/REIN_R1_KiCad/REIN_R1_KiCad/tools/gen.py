#!/usr/bin/env python3
"""MMARAU R1 - KiCad project generator (schematic v0.1)."""
import uuid, math, os, csv, json, re, sys, collections

OUT = sys.argv[1] if len(sys.argv) > 1 else "out"
PROJ = "REIN_R1"
ROOT = str(uuid.uuid4())
def U(): return str(uuid.uuid4())
def f(x): return ("%.4f" % x).rstrip("0").rstrip(".")

FP = dict(
    R="Resistor_SMD:R_0402_1005Metric", R12="Resistor_SMD:R_1206_3216Metric",
    C="Capacitor_SMD:C_0402_1005Metric", C8="Capacitor_SMD:C_0805_2012Metric",
    L="Inductor_SMD:L_1210_3225Metric", LS="Inductor_SMD:L_Taiyo-Yuden_NR-40xx",
    LED="LED_SMD:LED_0603_1608Metric", SW="Button_Switch_SMD:SW_SPST_TL3342",
    SMB="Diode_SMD:D_SMB", SMA="Diode_SMD:D_SMA", SOD="Diode_SMD:D_SOD-123",
    FUSE="Fuse:Fuse_1206_3216Metric", SOT23="Package_TO_SOT_SMD:SOT-23",
    SOT235="Package_TO_SOT_SMD:SOT-23-5", SOT236="Package_TO_SOT_SMD:SOT-23-6",
    QFN56="Package_DFN_QFN:QFN-56-1EP_7x7mm_P0.4mm_EP3.2x3.2mm",
    QFN24="Package_DFN_QFN:QFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm",
    DFN8="REIN:DFN-8-1EP_2x2mm_P0.5mm_EP0.7x1.3mm",
    SOIC8W="REIN:SOIC-8_5.23x5.23mm_P1.27mm", SOIC8="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    SOIC16W="Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm", TSSOP20="Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm",
    VSSOP10="REIN:VSSOP-10_3x3mm_P0.5mm", XTAL="Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
    USBC="REIN:USB_C_Receptacle_HRO_TYPE-C-31-M-12", ESP="RF_Module:ESP32-S3-WROOM-1",
    JSTPH2="Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal",
    QWIIC="Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal",
    GROVE="Connector_JST:JST_PH_B4B-PH-K_1x04_P2.00mm_Vertical",
    TERM2="REIN:TerminalBlock_bornier-2_P5.08mm",
    SOCK40="Connector_PinSocket_2.54mm:PinSocket_2x20_P2.54mm_Vertical",
    SD="REIN:microSD_HC_Hirose_DM3AT-SF-PEJM5",
    BATT="Battery:BatteryHolder_Keystone_3034_1x20mm",
)
def hdr(n): return "Connector_PinHeader_2.54mm:PinHeader_1x%02d_P2.54mm_Vertical" % n

class Part:
    def __init__(s, ref, lib, value, fp, pins, sec, conf="ok", dnp=False, hide_names=False, note=""):
        s.ref, s.lib, s.value, s.fp, s.pins = ref, lib, value, fp, pins
        s.sec, s.conf, s.dnp, s.hide_names, s.note = sec, conf, dnp, hide_names, note
        s.x = s.y = 0
parts = []
cnt = collections.Counter()
def nref(p): cnt[p] += 1; return "%s%d" % (p, cnt[p])
def add(*a, **k):
    p = Part(*a, **k); parts.append(p); return p

# pin tuple: (number, name, etype, net)  etype: p passive, i power_in, o power_out
def two(ref, lib, value, fp, n1, n2, sec, names=("1", "2"), **k):
    return add(ref, lib, value, fp, [("1", names[0], "p", n1), ("2", names[1], "p", n2)], sec, hide_names=True, **k)
def R(a, b, v, sec, fp=None, **k): return two(nref("R"), "R", v, fp or FP["R"], a, b, sec, **k)
def C(a, b, v, sec, fp=None, **k): return two(nref("C"), "C", v, fp or FP["C"], a, b, sec, **k)
def L(a, b, v, sec, fp=None): return two(nref("L"), "L", v, fp or FP["L"], a, b, sec)
def D(k, a, v, fp, sec, lib="D", ref=None, **kw): return two(ref or nref("D"), lib, v, fp, k, a, sec, names=("K", "A"), **kw)
def SW(a, b, v, sec, ref=None): return two(ref or nref("SW"), "SW", v, FP["SW"], a, b, sec)
def decap(net, sec, n=1, v="100n"):
    for _ in range(n): C(net, "GND", v, sec)

def gen(ref, lib, value, fp, spec, sec, ep=None, conf="ok", note=""):
    """spec: list of (name, etype, net) numbered 1..N ; ep: net for exposed pad N+1"""
    pins = [(str(i + 1), n, t, net) for i, (n, t, net) in enumerate(spec)]
    if ep: pins.append((str(len(spec) + 1), "EP", "i", ep))
    return add(ref, lib, value, fp, pins, sec, conf=conf, note=note)

# ---------------------------------------------------------------- RP2040 block
RP_GPIO_PIN = {0:2,1:3,2:4,3:5,4:6,5:7,6:8,7:9,8:11,9:12,10:13,11:14,12:15,13:16,14:17,15:18,
               16:27,17:28,18:29,19:30,20:31,21:32,22:34,23:35,24:36,25:37,26:38,27:39,28:40,29:41}
RP_NAMES = {38:"GPIO26_ADC0",39:"GPIO27_ADC1",40:"GPIO28_ADC2",41:"GPIO29_ADC3"}
def rp2040(ref, flashref, xref, sec, sfx, gpio, usb_dp, usb_dm, swclk, swdio, run, vcc="3V3"):
    v11 = "1V1_" + sfx
    pins = {}
    for g, p in RP_GPIO_PIN.items():
        pins[p] = ("GPIO%d" % g if p not in RP_NAMES else RP_NAMES[p], "p", gpio.get(g))
    for p in (1, 10, 22, 33, 42, 49): pins[p] = ("IOVDD", "i", vcc)
    pins[19] = ("TESTEN", "p", "GND"); pins[20] = ("XIN", "p", "XIN_" + sfx); pins[21] = ("XOUT", "p", "XOUT_" + sfx)
    pins[23] = ("DVDD", "i", v11); pins[50] = ("DVDD", "i", v11)
    pins[24] = ("SWCLK", "p", swclk); pins[25] = ("SWD", "p", swdio); pins[26] = ("RUN", "p", run)
    pins[43] = ("ADC_AVDD", "i", vcc); pins[44] = ("VREG_VIN", "i", vcc); pins[45] = ("VREG_VOUT", "o", v11)
    pins[46] = ("USB_DM", "p", usb_dm); pins[47] = ("USB_DP", "p", usb_dp); pins[48] = ("USB_VDD", "i", vcc)
    pins[51] = ("QSPI_SD3", "p", "QSPI_SD3_" + sfx); pins[52] = ("QSPI_SCLK", "p", "QSPI_SCLK_" + sfx)
    pins[53] = ("QSPI_SD0", "p", "QSPI_SD0_" + sfx); pins[54] = ("QSPI_SD2", "p", "QSPI_SD2_" + sfx)
    pins[55] = ("QSPI_SD1", "p", "QSPI_SD1_" + sfx); pins[56] = ("QSPI_SS", "p", "QSPI_SS_" + sfx)
    pins[57] = ("GND", "i", "GND")
    plist = [(str(p), pins[p][0], pins[p][1], pins[p][2]) for p in sorted(pins)]
    add(ref, "RP2040", "RP2040", FP["QFN56"], plist, sec)
    # flash
    gen(flashref, "W25Q128JV", "W25Q128JVSIQ" if sfx == "T" else "W25Q16JV", FP["SOIC8W"],
        [("CS#", "p", "QSPI_SS_" + sfx), ("DO/IO1", "p", "QSPI_SD1_" + sfx), ("WP#/IO2", "p", "QSPI_SD2_" + sfx),
         ("GND", "i", "GND"), ("DI/IO0", "p", "QSPI_SD0_" + sfx), ("CLK", "p", "QSPI_SCLK_" + sfx),
         ("HOLD#/IO3", "p", "QSPI_SD3_" + sfx), ("VCC", "i", vcc)], sec)
    C(vcc, "GND", "100n", sec)
    # crystal
    add(xref, "XTAL4", "12MHz", FP["XTAL"], [("1", "XIN", "p", "XIN_" + sfx), ("2", "GND", "i", "GND"),
        ("3", "XOUT", "p", "XOUT_R_" + sfx), ("4", "GND", "i", "GND")], sec)
    R("XOUT_" + sfx, "XOUT_R_" + sfx, "1k", sec)
    C("XIN_" + sfx, "GND", "15p", sec); C("XOUT_R_" + sfx, "GND", "15p", sec)
    # decoupling
    decap(vcc, sec, 8); decap(v11, sec, 2); decap(vcc, sec, 1, "1u"); decap(v11, sec, 1, "1u")
    # bootsel
    R("QSPI_SS_" + sfx, "BOOTR_" + sfx, "1k", sec)
    SW("BOOTR_" + sfx, "GND", "BOOTSEL", sec)

# ================================================================= SECTIONS
S_USB, S_PWR, S_CHG, S_TGT, S_PRB, S_HUB, S_ESP, S_ANA, S_SYS, S_CON, S_BB, S_FLG = (
    "1 USB-C + PD + hub", "2 Power input + 5V", "3 Charger, fuel gauge, 3V3", "4 RP2040 target (main MCU)",
    "5 RP2040 debug probe", "6 USB hub + ESD", "7 ESP32-S3 + microSD", "8 Analog + secure + RTC",
    "9 Bus A devices, Qwiic/Grove", "10 Pi 5 HAT header + debug headers", "11 Breadboard / level shifters", "12 Power flags")

# ---- USB-C connector
usbc = [("A1","GND"),("A4","VBUS"),("A5","CC1"),("A6","USB_DP_C"),("A7","USB_DM_C"),("A8",None),("A9","VBUS"),("A12","GND"),
        ("B1","GND"),("B4","VBUS"),("B5","CC2"),("B6","USB_DP_C"),("B7","USB_DM_C"),("B8",None),("B9","VBUS"),("B12","GND"),("S1","GND")]
add("J1", "USB_C_16P", "USB-C (HRO TYPE-C-31-M-12)", FP["USBC"],
    [(n, n, "p", net) for n, net in usbc], S_USB)
R("CC1", "GND", "5.1k", S_USB, dnp=True, note="Fit ONLY if PD controller U18 is removed")
R("CC2", "GND", "5.1k", S_USB, dnp=True, note="Fit ONLY if PD controller U18 is removed")
D("VBUS", "GND", "SMBJ24A", FP["SMB"], S_USB, lib="TVS", ref="D1")
gen("U19", "USBLC6-2SC6", "USBLC6-2SC6", FP["SOT236"],
    [("IO1", "p", "USB_DP_C"), ("GND", "i", "GND"), ("IO2", "p", "USB_DM_C"), ("IO2b", "p", "USB_DM_C"),
     ("VBUS", "i", "VBUS"), ("IO1b", "p", "USB_DP_C")], S_USB)
gen("U18", "PD_SINK_GENERIC", "STUSB4500 (QFN-24)", FP["QFN24"],
    [("CC1", "p", "CC1"), ("CC2", "p", "CC2"), ("VBUS_SENSE", "p", "VBUS"), ("VBUS_EN_SNK", "p", None),
     ("SDA", "p", "I2CA_SDA"), ("SCL", "p", "I2CA_SCL"), ("ALERT", "p", "INT_PWR"), ("ADDR0", "p", "GND"),
     ("ADDR1", "p", "GND"), ("RESET", "p", "GND"), ("VDD", "i", "3V3"), ("VREG", "p", None),
     ("N1", "p", None), ("N2", "p", None), ("N3", "p", None), ("N4", "p", None), ("N5", "p", None), ("N6", "p", None),
     ("N7", "p", None), ("N8", "p", None), ("N9", "p", None), ("N10", "p", None), ("N11", "p", None), ("GND", "i", "GND")],
    S_USB, ep="GND", conf="VERIFY", note="Generic pin order - replace with datasheet pinout")
decap("3V3", S_USB)

# ---- power input
add("J2", "CONN_2", "DC IN 6-36V", FP["TERM2"], [("1", "VDC+", "p", "VDC_RAW"), ("2", "GND", "p", "GND")], S_PWR)
D("VDC_RAW", "GND", "SMBJ33A", FP["SMB"], S_PWR, lib="TVS", ref="D2")
add("Q1", "PFET", "P-MOSFET 40V (reverse protect)", FP["SOT23"],
    [("1", "G", "p", "Q1_G"), ("2", "S", "p", "VDC_PROT"), ("3", "D", "p", "VDC_RAW")], S_PWR)
R("Q1_G", "GND", "100k", S_PWR)
D("VDC_PROT", "Q1_G", "BZX84-10V", FP["SOD"], S_PWR, lib="ZENER", ref="DZ1")
D("VIN", "VBUS", "SS34", FP["SMA"], S_PWR, ref="D3")
D("VIN", "VDC_PROT", "SS34", FP["SMA"], S_PWR, ref="D4")
decap("VIN", S_PWR, 2, "10u")
gen("U7", "BUCK_WIDE_5V", "Wide-in buck 5V (TPS54202-class)", FP["SOT236"],
    [("GND", "i", "GND"), ("SW", "p", "BK5_SW"), ("VIN", "i", "VIN"), ("FB", "p", "BK5_FB"),
     ("EN", "p", "VIN"), ("BST", "p", "BK5_BST")], S_PWR, conf="VERIFY",
    note="Pin order from TPS54202 family - verify; check 36V rating of final part")
C("BK5_BST", "BK5_SW", "100n", S_PWR)
L("BK5_SW", "5V_BUCK", "10u", S_PWR)
gen("U8", "INA226", "INA226AIDGSR", FP["VSSOP10"],
    [("A1", "p", "GND"), ("A0", "p", "GND"), ("ALERT", "p", "INT_PWR"), ("SDA", "p", "I2CA_SDA"), ("SCL", "p", "I2CA_SCL"),
     ("VS", "i", "3V3"), ("GND", "i", "GND"), ("VBUS", "p", "5V"), ("IN-", "p", "5V"), ("IN+", "p", "5V_F")], S_PWR)
decap("3V3", S_PWR)
R("5V_BUCK", "BK5_FB", "732k", S_PWR); R("BK5_FB", "GND", "100k", S_PWR)
decap("5V_BUCK", S_PWR, 1, "22u")
add("F1", "FUSE", "PTC 2A", FP["FUSE"], [("1", "1", "p", "5V_BUCK"), ("2", "2", "p", "5V_F")], S_PWR, hide_names=True)
two("RSH1", "R", "20m shunt", FP["R12"], "5V_F", "5V", S_PWR)
D("5V", "PI_5V", "SS14", FP["SOD"], S_PWR, ref="D7")
decap("5V", S_PWR, 2, "10u")

# ---- charger / gauge / 3V3
gen("U9", "MCP73831", "MCP73831T-2ACI/OT", FP["SOT235"],
    [("STAT", "p", "CHG_STAT"), ("VSS", "i", "GND"), ("VBAT", "p", "VBAT"), ("VDD", "i", "5V"), ("PROG", "p", "CHG_PROG")], S_CHG)
R("CHG_PROG", "GND", "2k", S_CHG); decap("5V", S_CHG, 1, "10u"); decap("VBAT", S_CHG, 1, "10u")
R("5V", "CHG_LED_A", "1k", S_CHG)
D("CHG_STAT", "CHG_LED_A", "CHG (red)", FP["LED"], S_CHG, lib="LED", ref="D8")
add("J3", "CONN_2", "LiPo (JST-PH)", FP["JSTPH2"], [("1", "+", "p", "VBAT"), ("2", "-", "p", "GND"), ("MP", "MP", "p", "GND")], S_CHG)
gen("U10", "MAX17048", "MAX17048G+T10", FP["DFN8"],
    [("CELL", "p", "VBAT"), ("VDD", "i", "VBAT"), ("GND", "i", "GND"), ("QSTRT", "p", "GND"),
     ("SDA", "p", "I2CA_SDA"), ("SCL", "p", "I2CA_SCL"), ("ALRT", "p", "INT_PWR"), ("CTG", "p", "GND")],
    S_CHG, ep="GND", conf="VERIFY", note="Pin order from memory - verify against datasheet")
decap("VBAT", S_CHG)
D("VSYS", "5V", "SS14", FP["SOD"], S_CHG, ref="D5")
D("VSYS", "VBAT", "SS14", FP["SOD"], S_CHG, ref="D6")
decap("VSYS", S_CHG, 1, "10u")
gen("U11", "TLV62569", "TLV62569DBV", FP["SOT235"],
    [("EN", "p", "VSYS"), ("GND", "i", "GND"), ("SW", "p", "BK3_SW"), ("VIN", "i", "VSYS"), ("FB", "p", "BK3_FB")], S_CHG)
L("BK3_SW", "3V3", "2.2u", S_CHG, FP["LS"])
R("3V3", "BK3_FB", "1M", S_CHG); R("BK3_FB", "GND", "221k", S_CHG)
decap("3V3", S_CHG, 1, "22u"); decap("3V3", S_CHG, 1, "22u")
R("3V3", "PWR_LED_A", "1k", S_CHG)
D("GND", "PWR_LED_A", "PWR (green)", FP["LED"], S_CHG, lib="LED", ref="D9")

# ---- target RP2040
GP_T = {0:"DBG_TX",1:"DBG_RX",2:"I2CQ_SDA",3:"I2CQ_SCL",4:"I2CA_SDA",5:"I2CA_SCL",6:"INT_PWR",7:"RTC_INT",
        8:"PI_RXD",9:"PI_TXD",10:"PI_SCLK",11:"PI_MISO",12:"PI_MOSI",13:"PI_CE0",14:"ESP_HS",15:"ESP_DRDY",
        16:"ESP_MISO",17:"ESP_CS",18:"ESP_SCK",19:"ESP_MOSI",20:"ESP_EN",21:"ESP_IO0",
        22:"RP_IO22",23:"RP_IO23",24:"RP_IO24",25:"RP_IO25",26:"RP_IO26",27:"RP_IO27",28:"QWIIC_EN",29:"VSYS_SENSE"}
rp2040("U1", "U2", "Y1", S_TGT, "T", GP_T, "USB_T_DP", "USB_T_DM", "SWCLK", "SWDIO", "RUN_T")
SW("RUN_T", "GND", "RESET", S_TGT)
R("VSYS", "VSYS_SENSE", "100k", S_TGT); R("VSYS_SENSE", "GND", "100k", S_TGT); C("VSYS_SENSE", "GND", "100n", S_TGT)
R("I2CA_SDA", "3V3", "2.2k", S_TGT); R("I2CA_SCL", "3V3", "2.2k", S_TGT)
R("INT_PWR", "3V3", "10k", S_TGT); R("RTC_INT", "3V3", "10k", S_TGT)

# ---- probe RP2040
GP_P = {1:"RUN_T",2:"SWCLK",3:"SWDIO",4:"DBG_RX",5:"DBG_TX"}
rp2040("U3", "U4", "Y2", S_PRB, "P", GP_P, "USB_P_DP", "USB_P_DM", None, None, "RUN_P")
SW("RUN_P", "GND", "PROBE RESET", S_PRB)
R("USB_P_DP_H", "USB_P_DP", "27R", S_PRB); R("USB_P_DM_H", "USB_P_DM", "27R", S_PRB)

# ---- hub
R("HUB_DP1", "USB_T_DP", "27R", S_HUB); R("HUB_DM1", "USB_T_DM", "27R", S_HUB)
# note: probe series resistors above connect HUB_DP2/DM2 side
parts[-4].pins[0] = ("1", "1", "p", "HUB_DP2"); parts[-3].pins[0] = ("1", "1", "p", "HUB_DM2")
for p in parts:
    if p.pins and p.pins[0][3] in ("USB_P_DP_H", "USB_P_DM_H"):
        p.pins[0] = (p.pins[0][0], p.pins[0][1], "p", "HUB_DP2" if p.pins[0][3] == "USB_P_DP_H" else "HUB_DM2")
gen("U17", "USB_HUB_4P_GENERIC", "USB2.0 4-port hub (CH334-class)", FP["QFN24"],
    [("UP_DP", "p", "USB_DP_C"), ("UP_DM", "p", "USB_DM_C"), ("DP1", "p", "HUB_DP1"), ("DM1", "p", "HUB_DM1"),
     ("DP2", "p", "HUB_DP2"), ("DM2", "p", "HUB_DM2"), ("DP3", "p", "USB_E_DP"), ("DM3", "p", "USB_E_DM"),
     ("DP4", "p", None), ("DM4", "p", None), ("VDD33", "i", "3V3"), ("VBUS_DET", "p", "VBUS"), ("RST#", "p", None),
     ("N1", "p", None), ("N2", "p", None), ("N3", "p", None), ("N4", "p", None), ("N5", "p", None), ("N6", "p", None),
     ("N7", "p", None), ("N8", "p", None), ("N9", "p", None), ("N10", "p", None), ("GND", "i", "GND")],
    S_HUB, ep="GND", conf="VERIFY", note="Generic pin order - replace with datasheet pinout of the chosen hub IC")
decap("3V3", S_HUB, 2)

# ---- ESP32-S3
esp = {1:("GND","i","GND"),2:("3V3","i","3V3"),3:("EN","p","ESP_EN"),4:("IO4","p","ESP_B1"),5:("IO5","p","ESP_B2"),
       6:("IO6","p","ESP_B3"),7:("IO7","p","ESP_B4"),8:("IO15","p","ESP_B5"),9:("IO16","p","ESP_B6"),
       10:("IO17","p","ESP_B7"),11:("IO18","p","ESP_B8"),12:("IO8","p",None),13:("IO19_USB_DM","p","USB_E_DM"),
       14:("IO20_USB_DP","p","USB_E_DP"),15:("IO3","p",None),16:("IO46","p",None),17:("IO9","p","ESP_DRDY"),
       18:("IO10","p","ESP_CS"),19:("IO11","p","ESP_MOSI"),20:("IO12","p","ESP_SCK"),21:("IO13","p","ESP_MISO"),
       22:("IO14","p","ESP_HS"),23:("IO21","p","SD_D3"),24:("IO47","p",None),25:("IO48","p",None),26:("IO45","p",None),
       27:("IO0","p","ESP_IO0"),28:("IO35","p",None),29:("IO36","p",None),30:("IO37","p",None),31:("IO38","p","SD_D2"),
       32:("IO39","p","SD_CMD"),33:("IO40","p","SD_CLK"),34:("IO41","p","SD_D0"),35:("IO42","p","SD_D1"),
       36:("RXD0_IO44","p","ESP_RXD0"),37:("TXD0_IO43","p","ESP_TXD0"),38:("IO2","p","LED_USR"),39:("IO1","p",None),
       40:("GND","i","GND"),41:("GND_EP","i","GND")}
add("U5", "ESP32-S3-WROOM-1", "ESP32-S3-WROOM-1-N8", FP["ESP"], [(str(k), v[0], v[1], v[2]) for k, v in esp.items()], S_ESP)
decap("3V3", S_ESP, 1, "22u"); decap("3V3", S_ESP, 1)
R("3V3", "ESP_EN", "10k", S_ESP); C("ESP_EN", "GND", "1u", S_ESP); SW("ESP_EN", "GND", "ESP RESET", S_ESP)
R("3V3", "ESP_IO0", "10k", S_ESP); SW("ESP_IO0", "GND", "ESP BOOT", S_ESP)
R("LED_USR", "LED_USR_A", "1k", S_ESP)
D("GND", "LED_USR_A", "BT / USER (blue)", FP["LED"], S_ESP, lib="LED", ref="D10")
sd = [("DAT2","SD_D2"),("DAT3/CD","SD_D3"),("CMD","SD_CMD"),("VDD","3V3"),("CLK","SD_CLK"),("VSS","GND"),
      ("DAT0","SD_D0"),("DAT1","SD_D1"),("DET",None),("SH1","GND"),("SH2","GND")]
add("J4", "MICROSD", "microSD (Hirose DM3AT)", FP["SD"], [(str(i + 1), n, "p", net) for i, (n, net) in enumerate(sd)], S_ESP, conf="VERIFY",
    note="Pin names from memory; shield pins 10/11 to GND, DET unused")
for n in ("SD_D0", "SD_D1", "SD_D2", "SD_D3", "SD_CMD"): R(n, "3V3", "10k", S_ESP)
decap("3V3", S_ESP, 1, "10u")

# ---- analog / secure / RTC
gen("U12", "REF3033", "REF3033 (3.3V ref)", FP["SOT23"], [("VIN", "i", "VSYS"), ("VOUT", "p", "VREF_3V3"), ("GND", "i", "GND")],
    S_ANA, conf="VERIFY", note="Pin order generic - verify; VSYS must exceed ~3.4V for regulation")
decap("VSYS", S_ANA, 1, "1u"); decap("VREF_3V3", S_ANA, 1, "1u"); decap("VREF_3V3", S_ANA, 1, "100n")
add("FB1", "FB", "Ferrite 600R", FP["R"], [("1", "1", "p", "3V3"), ("2", "2", "p", "3V3_A")], S_ANA, hide_names=True)
decap("3V3_A", S_ANA, 1, "10u")
gen("U13", "ADS1115", "ADS1115IDGSR", FP["VSSOP10"],
    [("ADDR", "p", "GND"), ("ALERT/RDY", "p", None), ("GND", "i", "GND"), ("AIN0", "p", "AIN0"), ("AIN1", "p", "AIN1"),
     ("AIN2", "p", "AIN2"), ("AIN3", "p", "AIN3"), ("VDD", "i", "3V3_A"), ("SDA", "p", "I2CA_SDA"), ("SCL", "p", "I2CA_SCL")], S_ANA)
decap("3V3_A", S_ANA)
for i in range(4): R("AIN%d_H" % i, "AIN%d" % i, "1k", S_ANA)
gen("U14", "MCP4725", "MCP4725A1T-E/CH", FP["SOT236"],
    [("VOUT", "p", "DAC_OUT"), ("VSS", "i", "GND"), ("VDD", "i", "VREF_3V3"), ("SDA", "p", "I2CA_SDA"),
     ("SCL", "p", "I2CA_SCL"), ("A0", "p", "GND")], S_ANA)
R("DAC_OUT", "AOUT_H", "100R", S_ANA)
gen("U15", "ATECC608B", "ATECC608B-SSHDA", FP["SOIC8"],
    [("NC1", "p", None), ("NC2", "p", None), ("NC3", "p", None), ("GND", "i", "GND"), ("SDA", "p", "I2CA_SDA"),
     ("SCL", "p", "I2CA_SCL"), ("NC7", "p", None), ("VCC", "i", "3V3")], S_ANA)
decap("3V3", S_ANA)
gen("U16", "DS3231", "DS3231SN#", FP["SOIC16W"],
    [("32KHZ", "p", None), ("VCC", "i", "3V3"), ("INT#/SQW", "p", "RTC_INT"), ("RST#", "p", None)] +
    [("NC%d" % i, "p", None) for i in range(5, 13)] +
    [("GND", "i", "GND"), ("VBAT", "p", "RTC_VBAT"), ("SDA", "p", "I2CA_SDA"), ("SCL", "p", "I2CA_SCL")], S_ANA)
decap("3V3", S_ANA)
add("BT1", "BATT", "CR1220", FP["BATT"], [("1", "+", "p", "RTC_VBAT"), ("2", "-", "p", "GND")], S_ANA)
decap("RTC_VBAT", S_ANA)

# ---- bus A leftovers + Qwiic/Grove
add("J5", "CONN_4", "OLED 0.91in (GND VCC SCL SDA)", hdr(4),
    [("1", "GND", "p", "GND"), ("2", "VCC", "p", "3V3"), ("3", "SCL", "p", "I2CA_SCL"), ("4", "SDA", "p", "I2CA_SDA")], S_SYS)
gen("U20", "LOADSW", "TPS22918 (Qwiic switch)", FP["SOT236"],
    [("VIN", "i", "3V3"), ("GND", "i", "GND"), ("ON", "p", "QWIIC_EN"), ("CT", "p", None), ("NC", "p", None), ("VOUT", "p", "Q3V3")],
    S_SYS, conf="VERIFY", note="Pin order generic - verify")
decap("3V3", S_SYS); decap("Q3V3", S_SYS, 1, "1u")
R("I2CQ_SDA", "Q3V3", "4.7k", S_SYS); R("I2CQ_SCL", "Q3V3", "4.7k", S_SYS)
for r in ("J6", "J7"):
    add(r, "QWIIC", "Qwiic (SH 4-pin)", FP["QWIIC"],
        [("1", "GND", "p", "GND"), ("2", "3V3", "p", "Q3V3"), ("3", "SDA", "p", "I2CQ_SDA"), ("4", "SCL", "p", "I2CQ_SCL"),
         ("MP", "MP", "p", "GND")], S_SYS)
add("J8", "GROVE", "Grove I2C (PH 4-pin)", FP["GROVE"],
    [("1", "SCL", "p", "I2CQ_SCL"), ("2", "SDA", "p", "I2CQ_SDA"), ("3", "VCC", "p", "Q3V3"), ("4", "GND", "p", "GND")], S_SYS)

# ---- Pi header + debug headers
pi = {i: None for i in range(1, 41)}
pi.update({2:"PI_5V",4:"PI_5V",6:"GND",8:"PI_TXD",9:"GND",10:"PI_RXD",14:"GND",19:"PI_MOSI",20:"GND",21:"PI_MISO",
           23:"PI_SCLK",24:"PI_CE0",25:"GND",27:"ID_SD",28:"ID_SC",30:"GND",34:"GND",39:"GND"})
add("J9", "PI_HEADER_2x20", "Pi 40-pin HAT socket", FP["SOCK40"], [(str(i), "P%d" % i, "p", pi[i]) for i in range(1, 41)], S_CON)
gen("U21", "CAT24C32", "CAT24C32WI (HAT ID EEPROM)", FP["SOIC8"],
    [("A0", "p", "GND"), ("A1", "p", "GND"), ("A2", "p", "GND"), ("VSS", "i", "GND"), ("SDA", "p", "ID_SD"),
     ("SCL", "p", "ID_SC"), ("WP", "p", "EE_WP"), ("VCC", "i", "3V3")], S_CON)
R("EE_WP", "3V3", "10k", S_CON); decap("3V3", S_CON)
add("J10", "CONN_2", "EEPROM WP jumper (short = writable)", hdr(2), [("1", "WP", "p", "EE_WP"), ("2", "GND", "p", "GND")], S_CON)
add("J11", "CONN_5", "SWD (CLK DIO GND RUN 3V3)", hdr(5),
    [("1", "SWCLK", "p", "SWCLK"), ("2", "SWDIO", "p", "SWDIO"), ("3", "GND", "p", "GND"), ("4", "RUN", "p", "RUN_T"), ("5", "3V3", "p", "3V3")], S_CON)
add("J12", "CONN_3", "Debug UART (GND TX RX)", hdr(3),
    [("1", "GND", "p", "GND"), ("2", "TX", "p", "DBG_TX"), ("3", "RX", "p", "DBG_RX")], S_CON)
add("J13", "CONN_4", "ESP UART (GND TX RX 3V3)", hdr(4),
    [("1", "GND", "p", "GND"), ("2", "TX", "p", "ESP_TXD0"), ("3", "RX", "p", "ESP_RXD0"), ("4", "3V3", "p", "3V3")], S_CON)

# ---- level shifters + breadboard headers
def txs(ref, a_nets, b_nets, sec):
    spec = [("A1", "p", a_nets[0]), ("VCCA", "i", "3V3"), ("A2", "p", a_nets[1]), ("A3", "p", a_nets[2]), ("A4", "p", a_nets[3]),
            ("A5", "p", a_nets[4]), ("A6", "p", a_nets[5]), ("A7", "p", a_nets[6]), ("A8", "p", a_nets[7]), ("OE", "p", "TXS_OE"),
            ("GND", "i", "GND"), ("B8", "p", b_nets[7]), ("B7", "p", b_nets[6]), ("B6", "p", b_nets[5]), ("B5", "p", b_nets[4]),
            ("B4", "p", b_nets[3]), ("B3", "p", b_nets[2]), ("B2", "p", b_nets[1]), ("VCCB", "i", "5V"), ("B1", "p", b_nets[0])]
    gen(ref, "TXS0108E", "TXS0108EPWR", FP["TSSOP20"], spec, sec)
    decap("3V3", sec); decap("5V", sec)
txs("U22", ["RP_IO22", "RP_IO23", "RP_IO24", "RP_IO25", "RP_IO26", "RP_IO27", None, None],
    ["BB_22", "BB_23", "BB_24", "BB_25", "BB_26", "BB_27", None, None], S_BB)
txs("U23", ["ESP_B%d" % i for i in range(1, 9)], ["BE_%d" % i for i in range(1, 9)], S_BB)
R("TXS_OE", "3V3", "10k", S_BB)
add("J14", "CONN_8", "Breadboard RP2040 5V I/O (22-27, 5V, GND)", hdr(8),
    [(str(i + 1), "IO%d" % (22 + i), "p", "BB_%d" % (22 + i)) for i in range(6)] + [("7", "5V", "p", "5V"), ("8", "GND", "p", "GND")], S_BB)
add("J15", "CONN_8", "Breadboard ESP32 5V I/O 1-8", hdr(8), [(str(i + 1), "E%d" % (i + 1), "p", "BE_%d" % (i + 1)) for i in range(8)], S_BB)
add("J16", "CONN_4", "Breadboard power (5V 3V3 GND GND)", hdr(4),
    [("1", "5V", "p", "5V"), ("2", "3V3", "p", "3V3"), ("3", "GND", "p", "GND"), ("4", "GND", "p", "GND")], S_BB)
add("J17", "CONN_6", "ADC in (AIN0-3, GND, 3V3_A)", hdr(6),
    [(str(i + 1), "AIN%d" % i, "p", "AIN%d_H" % i) for i in range(4)] + [("5", "GND", "p", "GND"), ("6", "3V3A", "p", "3V3_A")], S_BB)
add("J18", "CONN_2", "DAC out (AOUT, GND)", hdr(2), [("1", "AOUT", "p", "AOUT_H"), ("2", "GND", "p", "GND")], S_BB)

# ---- power flags
for i, n in enumerate(["GND", "3V3", "3V3_A", "5V", "VBAT", "VSYS", "VREF_3V3", "Q3V3", "VIN", "VBUS", "1V1_T", "1V1_P"]):
    if n.startswith("1V1"): continue  # driven by VREG_VOUT power_out
    add("#FLG%d" % (i + 1), "PWR_FLAG", "PWR_FLAG", "", [("1", "pwr", "o", n)], S_FLG, hide_names=True)

# ================================================================ SYMBOLS
ETYPE = {"p": "passive", "i": "power_in", "o": "power_out"}
def split_pins(p):
    pins = p.pins
    if p.lib == "PWR_FLAG": return [], list(pins)
    if len(pins) <= 2 or p.hide_names:
        return pins[:1], pins[1:]
    h = math.ceil(len(pins) / 2)
    return pins[:h], pins[h:]
def geom(p):
    Lp, Rp = split_pins(p)
    ml = max([len(x[1]) for x in Lp] or [0]); mr = max([len(x[1]) for x in Rp] or [0])
    n = max(len(Lp), len(Rp))
    wtxt = (ml + mr) * 1.15 + 4 if not p.hide_names else 6
    W = max(10.16, math.ceil(wtxt / 5.08) * 5.08)
    hw = W / 2
    hh = math.ceil((n + 1) / 2) * 2.54
    return Lp, Rp, hw, hh

_sigs = {}
for p in parts:
    sig = (tuple((x[0], x[1], x[2]) for x in p.pins), p.hide_names, p.dnp and False)
    lst = _sigs.setdefault(p.lib, [])
    if sig not in lst: lst.append(sig)
    idx = lst.index(sig)
    p.libkey = p.lib if idx == 0 else "%s_v%d" % (p.lib, idx + 1)
libdefs = {}
def symdef(p, prefix):
    Lp, Rp, hw, hh = geom(p)
    name = p.libkey
    ref0 = re.sub(r"[0-9]+$", "", p.ref)
    out = ['(symbol "%s%s" %s(in_bom %s) (on_board %s)' % (prefix, name,
           "(pin_names (offset 0.508) hide) (pin_numbers hide) " if p.hide_names else "(pin_names (offset 0.508)) ",
           "no" if p.ref.startswith("#") else "yes", "no" if p.ref.startswith("#") else "yes")]
    def prop(k, v, y, hide=False):
        return '(property "%s" "%s" (at 0 %s 0) (effects (font (size 1.27 1.27))%s))' % (k, v, f(y), " hide" if hide else "")
    out.append(prop("Reference", ref0, hh + 1.27)); out.append(prop("Value", name, -hh - 1.27))
    out.append(prop("Footprint", "", 0, True)); out.append(prop("Datasheet", "~", 0, True))
    out.append('(symbol "%s_0_1" (rectangle (start %s %s) (end %s %s) (stroke (width 0.254) (type default)) (fill (type background))))'
               % (name, f(-hw), f(hh), f(hw), f(-hh)))
    out.append('(symbol "%s_1_1"' % name)
    for side, lst in (("L", Lp), ("R", Rp)):
        for i, (num, pn, et, net) in enumerate(lst):
            y = hh - 2.54 * (i + 1)
            x = -hw - 2.54 if side == "L" else hw + 2.54
            ang = 0 if side == "L" else 180
            out.append('(pin %s line (at %s %s %d) (length 2.54) (name "%s" (effects (font (size 1.016 1.016)))) (number "%s" (effects (font (size 1.016 1.016)))))'
                       % (ETYPE[et], f(x), f(y), ang, pn, num))
    out.append(")")
    out.append(")")
    return "\n".join(out)

for p in parts:
    if p.libkey not in libdefs: libdefs[p.libkey] = p

# ================================================================ LAYOUT
def lblw(p):
    m = 4
    for pin in p.pins:
        if pin[3]: m = max(m, len(pin[3]))
    return m * 1.4 + 6
def ext(p):
    Lp, Rp, hw, hh = geom(p)
    return Lp, Rp, hw, hh, 2 * hw + 2 * (5.08 + lblw(p)), 2 * hh + 8
secs = []
for p in parts:
    if p.sec not in secs: secs.append(p.sec)
YMAX = 760; x_cursor = 30.48; title_texts = []; maxx = 0
for sec in secs:
    ps = [p for p in parts if p.sec == sec]
    title_texts.append((sec, x_cursor, 20.32))
    y = 38.1; colw = 0; col = []
    def flush():
        global x_cursor
        for (p, yy, w) in col:
            Lp, Rp, hw, hh, W, H = ext(p)
            cx = round((x_cursor + colw / 2) / 2.54) * 2.54
            p.x, p.y = cx, round((yy + H / 2) / 2.54) * 2.54
        x_cursor += colw + 12.7
    for p in ps:
        Lp, Rp, hw, hh, W, H = ext(p)
        if y + H > YMAX and col:
            flush(); col = []; y = 38.1; colw = 0
        col.append((p, y, W)); colw = max(colw, W); y += H + 6
    if col: flush()
    x_cursor += 12.7
PAGE_W = math.ceil(x_cursor / 10) * 10 + 20; PAGE_H = 841

# ================================================================ SCHEMATIC
sch = ['(kicad_sch (version 20230121) (generator rein_gen)', '(uuid "%s")' % ROOT,
       '(paper "User" %d %d)' % (PAGE_W, PAGE_H),
       '(title_block (title "REIN R1 - hybrid co-processor board") (date "2026-10-07") (rev "0.1-draft") '
       '(company "Reinford") (comment 1 "Generated draft - run ERC, verify VERIFY-tagged parts against datasheets"))',
       "(lib_symbols"]
for lib, p in libdefs.items(): sch.append(symdef(p, "REIN:"))
sch.append(")")
net_pins = collections.defaultdict(list)
nc_count = 0
for p in parts:
    Lp, Rp, hw, hh = geom(p)
    fields = [("Reference", p.ref, p.x - hw, p.y - hh - 2.54, False), ("Value", p.value, p.x, p.y + hh + 2.54, False),
              ("Footprint", p.fp, p.x, p.y, True), ("Datasheet", "~", p.x, p.y, True)]
    sch.append('(symbol (lib_id "REIN:%s") (at %s %s 0) (unit 1) (in_bom %s) (on_board %s) (dnp %s) (uuid "%s")' % (
        p.libkey, f(p.x), f(p.y), "no" if p.ref.startswith("#") else "yes", "no" if p.ref.startswith("#") else "yes",
        "yes" if p.dnp else "no", U()))
    for k, v, x, y, hide in fields:
        sch.append('(property "%s" "%s" (at %s %s 0) (effects (font (size 1.27 1.27))%s))' % (k, v, f(x), f(y), " hide" if hide else ""))
    for pin in p.pins: sch.append('(pin "%s" (uuid "%s"))' % (pin[0], U()))
    sch.append('(instances (project "%s" (path "/%s" (reference "%s") (unit 1))))' % (PROJ, ROOT, p.ref))
    sch.append(")")
    for side, lst in (("L", Lp), ("R", Rp)):
        for i, (num, pn, et, net) in enumerate(lst):
            py = p.y - (hh - 2.54 * (i + 1))
            px = p.x - hw - 2.54 if side == "L" else p.x + hw + 2.54
            if net is None:
                sch.append('(no_connect (at %s %s) (uuid "%s"))' % (f(px), f(py), U())); nc_count += 1
                continue
            ex = px - 2.54 if side == "L" else px + 2.54
            sch.append('(wire (pts (xy %s %s) (xy %s %s)) (stroke (width 0) (type default)) (uuid "%s"))' % (f(px), f(py), f(ex), f(py), U()))
            sch.append('(label "%s" (at %s %s %d) (effects (font (size 1.27 1.27)) (justify %s bottom)) (uuid "%s"))' % (
                net, f(ex), f(py), 180 if side == "L" else 0, "right" if side == "L" else "left", U()))
            net_pins[net].append((p.ref, num, pn))
for sec, x, y in title_texts:
    sch.append('(text "%s" (at %s %s 0) (effects (font (size 3.5 3.5) bold) (justify left bottom)) (uuid "%s"))' % (sec, f(x), f(y), U()))
sch.append('(sheet_instances (path "/" (page "1")))')
sch.append(")")

os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, PROJ + ".kicad_sch"), "w").write("\n".join(sch) + "\n")

# ---- symbol library file
sym = ["(kicad_symbol_lib (version 20220914) (generator rein_gen)"]
for lib, p in libdefs.items(): sym.append(symdef(p, ""))
sym.append(")")
open(os.path.join(OUT, "REIN.kicad_sym"), "w").write("\n".join(sym) + "\n")
open(os.path.join(OUT, "sym-lib-table"), "w").write(
    '(sym_lib_table\n  (version 7)\n  (lib (name "REIN")(type "KiCad")(uri "${KIPRJMOD}/REIN.kicad_sym")(options "")(descr "REIN R1 generated symbols"))\n)\n')
open(os.path.join(OUT, "fp-lib-table"), "w").write(
    '(fp_lib_table\n  (version 7)\n  (lib (name "REIN")(type "KiCad")(uri "${KIPRJMOD}/REIN.pretty")(options "")(descr "REIN R1 embedded footprints"))\n)\n')
EMBED = {"TerminalBlock_bornier-2_P5.08mm": "TerminalBlock", "VSSOP-10_3x3mm_P0.5mm": "Package_SO",
         "DFN-8-1EP_2x2mm_P0.5mm_EP0.7x1.3mm": "Package_DFN_QFN", "SOIC-8_5.23x5.23mm_P1.27mm": "Package_SO",
         "USB_C_Receptacle_HRO_TYPE-C-31-M-12": "Connector_USB", "microSD_HC_Hirose_DM3AT-SF-PEJM5": "Connector_Card"}
def strip_model(t):
    while True:
        i = t.find("(model ")
        if i < 0: return t
        d = 0; j = i
        while True:
            if t[j] == "(": d += 1
            elif t[j] == ")":
                d -= 1
                if d == 0: break
            j += 1
        t = t[:i].rstrip(" \t") + t[j + 1:]
os.makedirs(os.path.join(OUT, "REIN.pretty"), exist_ok=True)
for nm, lb in EMBED.items():
    src = open("/usr/share/kicad/footprints/%s.pretty/%s.kicad_mod" % (lb, nm)).read()
    open(os.path.join(OUT, "REIN.pretty", nm + ".kicad_mod"), "w").write(strip_model(src))
json.dump({"meta": {"filename": PROJ + ".kicad_pro", "version": 1}, "sheets": [[ROOT, "Root"]], "text_variables": {}},
          open(os.path.join(OUT, PROJ + ".kicad_pro"), "w"), indent=2)

# ---- PCB (outline only; import netlist with F8)
OX, OY, BW, BH = 60.0, 60.0, 85.0, 56.0
lay = ('(0 "F.Cu" signal)(1 "In1.Cu" signal)(2 "In2.Cu" signal)(31 "B.Cu" signal)(32 "B.Adhes" user "B.Adhesive")'
       '(33 "F.Adhes" user "F.Adhesive")(34 "B.Paste" user)(35 "F.Paste" user)(36 "B.SilkS" user "B.Silkscreen")'
       '(37 "F.SilkS" user "F.Silkscreen")(38 "B.Mask" user)(39 "F.Mask" user)(40 "Dwgs.User" user "User.Drawings")'
       '(41 "Cmts.User" user "User.Comments")(42 "Eco1.User" user "User.Eco1")(43 "Eco2.User" user "User.Eco2")'
       '(44 "Edge.Cuts" user)(45 "Margin" user)(46 "B.CrtYd" user "B.Courtyard")(47 "F.CrtYd" user "F.Courtyard")'
       '(48 "B.Fab" user)(49 "F.Fab" user)')
def gl(x1, y1, x2, y2, layer, w=0.1):
    return '(gr_line (start %s %s) (end %s %s) (stroke (width %s) (type default)) (layer "%s") (tstamp %s))' % (
        f(x1), f(y1), f(x2), f(y2), w, layer, U())
pcb = ['(kicad_pcb (version 20221018) (generator pcbnew)', '(general (thickness 1.6))', '(paper "A4")', "(layers %s)" % lay,
       "(setup (pad_to_mask_clearance 0) (pcbplotparams (layerselection 0x00010fc_ffffffff) (plot_on_all_layers_selection 0x0000000_00000000) (disableapertmacros false) (usegerberextensions false) (usegerberattributes true) (usegerberadvancedattributes true) (creategerberjobfile true) (svguseinch false) (svgprecision 6) (excludeedgelayer true) (plotframeref false) (viasonmask false) (mode 1) (useauxorigin false) (hpglpennumber 1) (hpglpenspeed 20) (hpglpendiameter 15.000000) (dxfpolygonmode true) (dxfimperialunits true) (dxfusepcbnewfont true) (psnegative false) (psa4output false) (plotreference true) (plotvalue true) (plotinvisibletext false) (sketchpadsonfab false) (subtractmaskfromsilk false) (outputformat 1) (mirror false) (drillshape 1) (scaleselection 1) (outputdirectory \"\")))",
       '(net 0 "")']
x1, y1, x2, y2 = OX, OY, OX + BW, OY + BH
for a in ((x1, y1, x2, y1), (x2, y1, x2, y2), (x2, y2, x1, y2), (x1, y2, x1, y1)): pcb.append(gl(*a, "Edge.Cuts", 0.1))
pcb.append(gl(OX + 65, OY, OX + 65, OY + BH, "Dwgs.User", 0.15))
pcb.append('(gr_text "HAT 65x56 | snap-off wing from x=65" (at %s %s) (layer "Cmts.User") (tstamp %s) (effects (font (size 1.5 1.5) (thickness 0.15))))' % (f(OX + 32), f(OY - 3), U()))
for hx, hy in ((3.5, 3.5), (61.5, 3.5), (3.5, 52.5), (61.5, 52.5)):
    pcb.append('(gr_circle (center %s %s) (end %s %s) (stroke (width 0.15) (type default)) (fill none) (layer "Cmts.User") (tstamp %s))' % (
        f(OX + hx), f(OY + hy), f(OX + hx + 1.35), f(OY + hy), U()))
pcb.append(")")
open(os.path.join(OUT, PROJ + ".kicad_pcb"), "w").write("\n".join(pcb) + "\n")

# ================================================================ REPORT FILES
with open(os.path.join(OUT, "REIN_R1_BOM.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["Ref", "Value", "Footprint", "DNP", "Confidence", "Note"])
    for p in parts:
        if p.ref.startswith("#"): continue
        w.writerow([p.ref, p.value, p.fp, "yes" if p.dnp else "", p.conf, p.note])
with open(os.path.join(OUT, "REIN_R1_NET_TABLE.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["Net", "Pin count", "Connections"])
    for n in sorted(net_pins): w.writerow([n, len(net_pins[n]), " ".join("%s.%s(%s)" % t for t in net_pins[n])])
with open(os.path.join(OUT, "REIN_R1_GPIO_MAP.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["MCU", "GPIO", "Net", "Function"])
    func = {"DBG_TX":"UART0 TX -> probe","DBG_RX":"UART0 RX <- probe","I2CQ_SDA":"I2C1 SDA (Qwiic/Grove)","I2CQ_SCL":"I2C1 SCL (Qwiic/Grove)",
            "I2CA_SDA":"I2C0 SDA (bus A)","I2CA_SCL":"I2C0 SCL (bus A)","INT_PWR":"Wired-OR alert: PD / INA226 / fuel gauge",
            "RTC_INT":"DS3231 INT/SQW","PI_RXD":"UART1 TX -> Pi RXD","PI_TXD":"UART1 RX <- Pi TXD","PI_SCLK":"SPI1 SCK (slave to Pi)",
            "PI_MISO":"SPI1 TX","PI_MOSI":"SPI1 RX","PI_CE0":"SPI1 CSn","ESP_HS":"Handshake with ESP32","ESP_DRDY":"Data-ready from ESP32",
            "ESP_MISO":"SPI0 RX","ESP_CS":"SPI0 CSn","ESP_SCK":"SPI0 SCK","ESP_MOSI":"SPI0 TX","ESP_EN":"ESP32 EN (reset)","ESP_IO0":"ESP32 IO0 (boot)",
            "QWIIC_EN":"Qwiic load switch enable","VSYS_SENSE":"ADC3: VSYS/2"}
    for g in range(30):
        n = GP_T[g]; w.writerow(["RP2040 target", "GP%d" % g, n, func.get(n, "5V level-shifted I/O" if n.startswith("RP_IO") else "")])
    for g, n in sorted(GP_P.items()): w.writerow(["RP2040 probe", "GP%d" % g, n, "debugprobe"])
    for k, v in esp.items():
        if v[2]: w.writerow(["ESP32-S3", v[0], v[2], ""])

print("parts:", len(parts), "nets:", len(net_pins), "NC flags:", nc_count, "page:", PAGE_W, "x", PAGE_H)
single = sorted(n for n, l in net_pins.items() if len(l) < 2)
print("single-pin nets:", single)
# footprint pad check
pads_bad = 0
for p in parts:
    if not p.fp: continue
    lib, name = p.fp.split(":")
    fn = ("%s/REIN.pretty/%s.kicad_mod" % (OUT, name)) if lib == "REIN" else "/usr/share/kicad/footprints/%s.pretty/%s.kicad_mod" % (lib, name)
    if not os.path.exists(fn): print("MISSING FOOTPRINT", p.ref, p.fp); pads_bad += 1; continue
    txt = open(fn).read()
    fp_pads = set(m.group(1) or m.group(2) for m in re.finditer(r'\(pad\s+(?:"([^"]*)"|([^\s")]+))', txt))
    fp_pads.discard(""); fp_pads.discard(None)
    sym_pads = set(x[0] for x in p.pins)
    if fp_pads != sym_pads:
        print("PAD MISMATCH %s %s: symbol-only=%s footprint-only=%s" % (p.ref, name, sorted(sym_pads - fp_pads), sorted(fp_pads - sym_pads))); pads_bad += 1
print("pad/footprint issues:", pads_bad)
