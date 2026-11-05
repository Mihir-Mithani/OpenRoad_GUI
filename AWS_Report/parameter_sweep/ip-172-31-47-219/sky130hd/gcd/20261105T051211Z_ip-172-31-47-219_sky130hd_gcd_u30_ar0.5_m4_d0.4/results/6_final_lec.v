module gcd (clk,
    req_rdy,
    req_val,
    reset,
    resp_rdy,
    resp_val,
    req_msg,
    resp_msg);
 input clk;
 output req_rdy;
 input req_val;
 input reset;
 input resp_rdy;
 output resp_val;
 input [31:0] req_msg;
 output [15:0] resp_msg;

 wire net262;
 wire net261;
 wire net260;
 wire net259;
 wire net258;
 wire net257;
 wire net256;
 wire net255;
 wire net253;
 wire net252;
 wire net242;
 wire net240;
 wire net234;
 wire net233;
 wire net_2;
 wire net_1;
 wire _032_;
 wire net39;
 wire net46;
 wire net47;
 wire net48;
 wire net49;
 wire net50;
 wire net51;
 wire net52;
 wire net53;
 wire net54;
 wire net40;
 wire net41;
 wire net42;
 wire net43;
 wire net44;
 wire net45;
 wire _018_;
 wire _017_;
 wire _016_;
 wire _015_;
 wire _014_;
 wire _013_;
 wire _012_;
 wire _011_;
 wire _010_;
 wire _009_;
 wire _008_;
 wire _007_;
 wire _006_;
 wire _005_;
 wire _004_;
 wire _035_;
 wire _034_;
 wire _033_;
 wire _031_;
 wire _030_;
 wire _029_;
 wire _028_;
 wire _027_;
 wire _026_;
 wire _025_;
 wire _024_;
 wire _023_;
 wire _022_;
 wire _021_;
 wire _020_;
 wire _019_;
 wire _001_;
 wire _002_;
 wire _003_;
 wire _036_;
 wire _037_;
 wire _038_;
 wire _039_;
 wire _040_;
 wire _041_;
 wire _042_;
 wire _043_;
 wire _044_;
 wire _045_;
 wire _046_;
 wire _047_;
 wire _048_;
 wire _049_;
 wire _050_;
 wire _051_;
 wire _052_;
 wire _053_;
 wire _054_;
 wire _055_;
 wire _056_;
 wire _057_;
 wire _058_;
 wire _059_;
 wire _060_;
 wire _061_;
 wire _062_;
 wire _063_;
 wire _064_;
 wire _065_;
 wire _066_;
 wire _067_;
 wire _068_;
 wire _069_;
 wire _070_;
 wire _071_;
 wire _072_;
 wire _073_;
 wire _074_;
 wire _075_;
 wire _076_;
 wire _077_;
 wire _078_;
 wire _079_;
 wire _080_;
 wire _081_;
 wire _082_;
 wire _083_;
 wire _084_;
 wire _085_;
 wire _086_;
 wire _087_;
 wire _088_;
 wire _089_;
 wire _090_;
 wire _091_;
 wire _092_;
 wire _093_;
 wire _094_;
 wire _095_;
 wire _096_;
 wire _097_;
 wire _098_;
 wire _099_;
 wire _100_;
 wire _101_;
 wire _102_;
 wire _103_;
 wire _104_;
 wire _105_;
 wire _106_;
 wire _107_;
 wire _108_;
 wire _109_;
 wire _110_;
 wire _111_;
 wire _112_;
 wire _113_;
 wire _114_;
 wire _115_;
 wire _116_;
 wire _117_;
 wire _118_;
 wire net3;
 wire net4;
 wire net5;
 wire net6;
 wire net7;
 wire net8;
 wire net9;
 wire net10;
 wire net11;
 wire net12;
 wire net13;
 wire net14;
 wire net15;
 wire net16;
 wire net17;
 wire net18;
 wire net19;
 wire net20;
 wire net21;
 wire net22;
 wire net23;
 wire net24;
 wire net25;
 wire net26;
 wire net27;
 wire net28;
 wire net29;
 wire net30;
 wire net31;
 wire net32;
 wire net33;
 wire net34;
 wire net38;
 wire net35;
 wire net36;
 wire net37;
 wire net55;
 wire net162;
 wire net163;
 wire net164;
 wire net165;
 wire net166;
 wire net169;
 wire net170;
 wire net171;
 wire net172;
 wire net177;
 wire net213;
 wire net219;
 wire net218;
 wire net220;
 wire net236;
 wire net237;
 wire net238;
 wire net239;
 wire net241;
 wire net244;
 wire net265;
 wire net245;
 wire net246;
 wire net247;
 wire net248;
 wire net249;
 wire net250;
 wire net251;
 wire net264;
 wire clknet_2_0__leaf_clk;
 wire clknet_0_clk;
 wire net160;
 wire net161;
 wire net167;
 wire net168;
 wire net214;
 wire net215;
 wire net216;
 wire net217;
 wire net266;
 wire net267;
 wire clknet_2_1__leaf_clk;
 wire clknet_2_2__leaf_clk;
 wire clknet_2_3__leaf_clk;
 wire net280;
 wire net301;
 wire net304;

 \ALU_16_0_16_0_16_unused_CO[14:0]_X_KOGGE_STONE  _119_ (._020__263(net262),
    ._016__243(net242),
    ._010__235(net234),
    ._001__156(net261),
    ._033__154(net260),
    ._031__152(net259),
    ._030__150(net258),
    ._029__148(net257),
    ._028__146(net256),
    ._027__144(net255),
    ._025__140(net253),
    ._024__138(net252),
    ._014__125(net240),
    ._009__119(net233),
    .A({_001_,
    _019_,
    _020_,
    _021_,
    _022_,
    _023_,
    _024_,
    _025_,
    _026_,
    _027_,
    _028_,
    _029_,
    _030_,
    _031_,
    _033_,
    _034_}),
    .B({_035_,
    _004_,
    _005_,
    _006_,
    _007_,
    _008_,
    _009_,
    _010_,
    _011_,
    _012_,
    _013_,
    _014_,
    _015_,
    _016_,
    _017_,
    _018_}),
    .BI(net_1),
    .CI(net_2),
    .Y({net45,
    net44,
    net43,
    net42,
    net41,
    net40,
    net54,
    net53,
    net52,
    net51,
    net50,
    net49,
    net48,
    net47,
    net46,
    net39}),
    .\CO[15] (_032_));
 sky130_fd_sc_hd__conb_1 _119__1 (.HI(net_1));
 sky130_fd_sc_hd__conb_1 _119__2 (.HI(net_2));
 sky130_fd_sc_hd__clkinv_1 _121_ (.A(_003_),
    .Y(_036_));
 sky130_fd_sc_hd__clkinv_1 _122_ (.A(_002_),
    .Y(_037_));
 sky130_fd_sc_hd__o21bai_4 _123_ (.A1(_037_),
    .A2(_032_),
    .B1_N(net280),
    .Y(_038_));
 sky130_fd_sc_hd__mux2_2 _124_ (.A0(net261),
    .A1(net9),
    .S(net267),
    .X(_039_));
 sky130_fd_sc_hd__or2_4 _125_ (.A(net38),
    .B(_002_),
    .X(_040_));
 sky130_fd_sc_hd__nand2b_1 _126_ (.A_N(net38),
    .B(_002_),
    .Y(_041_));
 sky130_fd_sc_hd__mux2i_1 _127_ (.A0(net251),
    .A1(net39),
    .S(net166),
    .Y(_042_));
 sky130_fd_sc_hd__nand2_1 _128_ (.A(net10),
    .B(net216),
    .Y(_043_));
 sky130_fd_sc_hd__o21ai_1 _129_ (.A1(net216),
    .A2(_042_),
    .B1(_043_),
    .Y(_044_));
 sky130_fd_sc_hd__mux2i_1 _130_ (.A0(_017_),
    .A1(net46),
    .S(net166),
    .Y(_045_));
 sky130_fd_sc_hd__nand2_1 _131_ (.A(net11),
    .B(net216),
    .Y(_046_));
 sky130_fd_sc_hd__o21ai_1 _132_ (.A1(net216),
    .A2(_045_),
    .B1(_046_),
    .Y(_047_));
 sky130_fd_sc_hd__mux2i_1 _133_ (.A0(net242),
    .A1(net47),
    .S(net166),
    .Y(_048_));
 sky130_fd_sc_hd__nand2_1 _134_ (.A(net12),
    .B(net216),
    .Y(_049_));
 sky130_fd_sc_hd__o21ai_1 _135_ (.A1(net216),
    .A2(_048_),
    .B1(_049_),
    .Y(_050_));
 sky130_fd_sc_hd__mux2i_1 _136_ (.A0(net241),
    .A1(net48),
    .S(net166),
    .Y(_051_));
 sky130_fd_sc_hd__nand2_1 _137_ (.A(net13),
    .B(net216),
    .Y(_052_));
 sky130_fd_sc_hd__o21ai_1 _138_ (.A1(net216),
    .A2(_051_),
    .B1(_052_),
    .Y(_053_));
 sky130_fd_sc_hd__mux2i_1 _139_ (.A0(net240),
    .A1(net49),
    .S(net166),
    .Y(_054_));
 sky130_fd_sc_hd__nand2_1 _140_ (.A(net15),
    .B(net216),
    .Y(_055_));
 sky130_fd_sc_hd__o21ai_1 _141_ (.A1(net216),
    .A2(_054_),
    .B1(_055_),
    .Y(_056_));
 sky130_fd_sc_hd__mux2i_1 _142_ (.A0(net239),
    .A1(net50),
    .S(net168),
    .Y(_057_));
 sky130_fd_sc_hd__nand2_1 _143_ (.A(net16),
    .B(net216),
    .Y(_058_));
 sky130_fd_sc_hd__o21ai_1 _144_ (.A1(net216),
    .A2(_057_),
    .B1(_058_),
    .Y(_059_));
 sky130_fd_sc_hd__mux2i_1 _145_ (.A0(net238),
    .A1(net51),
    .S(net168),
    .Y(_060_));
 sky130_fd_sc_hd__nand2_1 _146_ (.A(net17),
    .B(net216),
    .Y(_061_));
 sky130_fd_sc_hd__o21ai_1 _147_ (.A1(net216),
    .A2(_060_),
    .B1(_061_),
    .Y(_062_));
 sky130_fd_sc_hd__mux2i_1 _148_ (.A0(net237),
    .A1(net52),
    .S(_032_),
    .Y(_063_));
 sky130_fd_sc_hd__nand2_1 _149_ (.A(net18),
    .B(net216),
    .Y(_064_));
 sky130_fd_sc_hd__o21ai_1 _150_ (.A1(net216),
    .A2(_063_),
    .B1(_064_),
    .Y(_065_));
 sky130_fd_sc_hd__mux2i_1 _151_ (.A0(net234),
    .A1(net53),
    .S(net168),
    .Y(_066_));
 sky130_fd_sc_hd__nand2_1 _152_ (.A(net19),
    .B(net216),
    .Y(_067_));
 sky130_fd_sc_hd__o21ai_1 _153_ (.A1(net216),
    .A2(_066_),
    .B1(_067_),
    .Y(_068_));
 sky130_fd_sc_hd__mux2i_1 _154_ (.A0(net233),
    .A1(net54),
    .S(net168),
    .Y(_069_));
 sky130_fd_sc_hd__nand2_1 _155_ (.A(net20),
    .B(net217),
    .Y(_070_));
 sky130_fd_sc_hd__o21ai_1 _156_ (.A1(net216),
    .A2(_069_),
    .B1(_070_),
    .Y(_071_));
 sky130_fd_sc_hd__mux2i_1 _157_ (.A0(net250),
    .A1(net40),
    .S(net167),
    .Y(_072_));
 sky130_fd_sc_hd__nand2_1 _158_ (.A(net21),
    .B(net217),
    .Y(_073_));
 sky130_fd_sc_hd__o21ai_0 _159_ (.A1(net217),
    .A2(_072_),
    .B1(_073_),
    .Y(_074_));
 sky130_fd_sc_hd__mux2i_1 _160_ (.A0(net249),
    .A1(net41),
    .S(net167),
    .Y(_075_));
 sky130_fd_sc_hd__nand2_1 _161_ (.A(net22),
    .B(net217),
    .Y(_076_));
 sky130_fd_sc_hd__o21ai_1 _162_ (.A1(net217),
    .A2(_075_),
    .B1(_076_),
    .Y(_077_));
 sky130_fd_sc_hd__mux2i_1 _163_ (.A0(net248),
    .A1(net42),
    .S(net167),
    .Y(_078_));
 sky130_fd_sc_hd__nand2_1 _164_ (.A(net23),
    .B(net217),
    .Y(_079_));
 sky130_fd_sc_hd__o21ai_1 _165_ (.A1(net217),
    .A2(_078_),
    .B1(_079_),
    .Y(_080_));
 sky130_fd_sc_hd__mux2i_1 _166_ (.A0(net247),
    .A1(net43),
    .S(net167),
    .Y(_081_));
 sky130_fd_sc_hd__nand2_1 _167_ (.A(net24),
    .B(net217),
    .Y(_082_));
 sky130_fd_sc_hd__o21ai_1 _168_ (.A1(net217),
    .A2(_081_),
    .B1(_082_),
    .Y(_083_));
 sky130_fd_sc_hd__mux2i_1 _169_ (.A0(net246),
    .A1(net44),
    .S(net167),
    .Y(_084_));
 sky130_fd_sc_hd__nand2_1 _170_ (.A(net26),
    .B(net217),
    .Y(_085_));
 sky130_fd_sc_hd__o21ai_0 _171_ (.A1(net217),
    .A2(_084_),
    .B1(_085_),
    .Y(_086_));
 sky130_fd_sc_hd__mux2_1 _172_ (.A0(_034_),
    .A1(net3),
    .S(net266),
    .X(_087_));
 sky130_fd_sc_hd__mux2_1 _173_ (.A0(net260),
    .A1(net14),
    .S(net266),
    .X(_088_));
 sky130_fd_sc_hd__mux2_1 _174_ (.A0(net259),
    .A1(net25),
    .S(net266),
    .X(_089_));
 sky130_fd_sc_hd__mux2_1 _175_ (.A0(net258),
    .A1(net28),
    .S(net266),
    .X(_090_));
 sky130_fd_sc_hd__mux2_1 _176_ (.A0(net257),
    .A1(net29),
    .S(net266),
    .X(_091_));
 sky130_fd_sc_hd__mux2_2 _177_ (.A0(net256),
    .A1(net30),
    .S(net264),
    .X(_092_));
 sky130_fd_sc_hd__mux2_2 _178_ (.A0(net255),
    .A1(net31),
    .S(net264),
    .X(_093_));
 sky130_fd_sc_hd__mux2_1 _179_ (.A0(_026_),
    .A1(net32),
    .S(net264),
    .X(_094_));
 sky130_fd_sc_hd__mux2_1 _180_ (.A0(net253),
    .A1(net33),
    .S(net264),
    .X(_095_));
 sky130_fd_sc_hd__mux2_1 _181_ (.A0(net252),
    .A1(net34),
    .S(net267),
    .X(_096_));
 sky130_fd_sc_hd__mux2_1 _182_ (.A0(_023_),
    .A1(net4),
    .S(net267),
    .X(_097_));
 sky130_fd_sc_hd__mux2_1 _183_ (.A0(_022_),
    .A1(net5),
    .S(net267),
    .X(_098_));
 sky130_fd_sc_hd__mux2_1 _184_ (.A0(_021_),
    .A1(net6),
    .S(net267),
    .X(_099_));
 sky130_fd_sc_hd__mux2_2 _185_ (.A0(net262),
    .A1(net7),
    .S(net267),
    .X(_100_));
 sky130_fd_sc_hd__mux2_1 _186_ (.A0(_019_),
    .A1(net8),
    .S(net267),
    .X(_101_));
 sky130_fd_sc_hd__nor2_2 _187_ (.A(_040_),
    .B(_036_),
    .Y(net55));
 sky130_fd_sc_hd__a221o_1 _188_ (.A1(_112_),
    .A2(net265),
    .B1(net37),
    .B2(net55),
    .C1(net36),
    .X(_102_));
 sky130_fd_sc_hd__nor2b_1 _189_ (.A(net265),
    .B_N(net37),
    .Y(_103_));
 sky130_fd_sc_hd__nor4_1 _190_ (.A(net245),
    .B(net236),
    .C(net233),
    .D(net250),
    .Y(_104_));
 sky130_fd_sc_hd__nor4_1 _191_ (.A(net249),
    .B(net248),
    .C(net247),
    .D(net246),
    .Y(_105_));
 sky130_fd_sc_hd__nor4_1 _192_ (.A(net251),
    .B(net244),
    .C(net242),
    .D(net237),
    .Y(_106_));
 sky130_fd_sc_hd__nor4_1 _193_ (.A(net241),
    .B(net240),
    .C(net239),
    .D(net238),
    .Y(_107_));
 sky130_fd_sc_hd__and4_1 _194_ (.A(net215),
    .B(net214),
    .C(_106_),
    .D(net213),
    .X(_108_));
 sky130_fd_sc_hd__nand2_1 _195_ (.A(_032_),
    .B(_108_),
    .Y(_109_));
 sky130_fd_sc_hd__a21oi_1 _196_ (.A1(_032_),
    .A2(_108_),
    .B1(_003_),
    .Y(_110_));
 sky130_fd_sc_hd__o22ai_1 _197_ (.A1(_036_),
    .A2(_103_),
    .B1(_037_),
    .B2(_110_),
    .Y(_111_));
 sky130_fd_sc_hd__clkinv_1 _198_ (.A(net35),
    .Y(_112_));
 sky130_fd_sc_hd__nor2b_1 _199_ (.A(net36),
    .B_N(_111_),
    .Y(_113_));
 sky130_fd_sc_hd__a22oi_2 _200_ (.A1(net35),
    .A2(net265),
    .B1(_109_),
    .B2(_002_),
    .Y(_114_));
 sky130_fd_sc_hd__nor2_1 _201_ (.A(_114_),
    .B(net36),
    .Y(_115_));
 sky130_fd_sc_hd__mux2i_1 _202_ (.A0(net245),
    .A1(net45),
    .S(net167),
    .Y(_116_));
 sky130_fd_sc_hd__nand2_1 _203_ (.A(net27),
    .B(net217),
    .Y(_117_));
 sky130_fd_sc_hd__o21ai_1 _204_ (.A1(net217),
    .A2(_116_),
    .B1(_117_),
    .Y(_118_));
 sky130_fd_sc_hd__clkbuf_16 clkbuf_0_clk (.A(clk),
    .X(clknet_0_clk));
 sky130_fd_sc_hd__clkbuf_16 clkbuf_2_0__f_clk (.A(clknet_0_clk),
    .X(clknet_2_0__leaf_clk));
 sky130_fd_sc_hd__clkbuf_16 clkbuf_2_1__f_clk (.A(clknet_0_clk),
    .X(clknet_2_1__leaf_clk));
 sky130_fd_sc_hd__clkbuf_16 clkbuf_2_2__f_clk (.A(clknet_0_clk),
    .X(clknet_2_2__leaf_clk));
 sky130_fd_sc_hd__clkbuf_16 clkbuf_2_3__f_clk (.A(clknet_0_clk),
    .X(clknet_2_3__leaf_clk));
 sky130_fd_sc_hd__clkbuf_8 clkload0 (.A(clknet_2_0__leaf_clk));
 sky130_fd_sc_hd__clkbuf_1 clkload1 (.A(clknet_2_2__leaf_clk));
 sky130_fd_sc_hd__clkbuf_8 clkload2 (.A(clknet_2_3__leaf_clk));
 sky130_fd_sc_hd__dfxtp_4 \ctrl.state.out[0]$_DFF_P_  (.D(_102_),
    .Q(net38),
    .CLK(clknet_2_1__leaf_clk));
 sky130_fd_sc_hd__dfxtp_1 \ctrl.state.out[1]$_DFF_P_  (.D(_113_),
    .Q(_003_),
    .CLK(clknet_2_1__leaf_clk));
 sky130_fd_sc_hd__dfxtp_1 \ctrl.state.out[2]$_DFF_P_  (.D(_115_),
    .Q(_002_),
    .CLK(clknet_2_1__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[0]$_DFFE_PP_  (.D(_044_),
    .DE(net219),
    .Q(_034_),
    .CLK(clknet_2_1__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[10]$_DFFE_PP_  (.D(_074_),
    .DE(net218),
    .Q(_023_),
    .CLK(clknet_2_2__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[11]$_DFFE_PP_  (.D(_077_),
    .DE(net218),
    .Q(_022_),
    .CLK(clknet_2_3__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[12]$_DFFE_PP_  (.D(_080_),
    .DE(net218),
    .Q(_021_),
    .CLK(clknet_2_3__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[13]$_DFFE_PP_  (.D(_083_),
    .DE(net218),
    .Q(_020_),
    .CLK(clknet_2_3__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[14]$_DFFE_PP_  (.D(_086_),
    .DE(net218),
    .Q(_019_),
    .CLK(clknet_2_3__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[15]$_DFFE_PP_  (.D(_118_),
    .DE(net218),
    .Q(_001_),
    .CLK(clknet_2_2__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[1]$_DFFE_PP_  (.D(_047_),
    .DE(net219),
    .Q(_033_),
    .CLK(clknet_2_0__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[2]$_DFFE_PP_  (.D(_050_),
    .DE(net219),
    .Q(_031_),
    .CLK(clknet_2_1__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[3]$_DFFE_PP_  (.D(_053_),
    .DE(net219),
    .Q(_030_),
    .CLK(clknet_2_0__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[4]$_DFFE_PP_  (.D(_056_),
    .DE(net219),
    .Q(_029_),
    .CLK(clknet_2_0__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[5]$_DFFE_PP_  (.D(_059_),
    .DE(net220),
    .Q(_028_),
    .CLK(clknet_2_0__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[6]$_DFFE_PP_  (.D(_062_),
    .DE(net220),
    .Q(_027_),
    .CLK(clknet_2_2__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[7]$_DFFE_PP_  (.D(_065_),
    .DE(net220),
    .Q(_026_),
    .CLK(clknet_2_1__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[8]$_DFFE_PP_  (.D(_068_),
    .DE(net220),
    .Q(_025_),
    .CLK(clknet_2_2__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[9]$_DFFE_PP_  (.D(_071_),
    .DE(net220),
    .Q(_024_),
    .CLK(clknet_2_2__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[0]$_DFFE_PP_  (.D(_087_),
    .DE(net161),
    .Q(_018_),
    .CLK(clknet_2_1__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[10]$_DFFE_PP_  (.D(_097_),
    .DE(net160),
    .Q(_008_),
    .CLK(clknet_2_2__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[11]$_DFFE_PP_  (.D(_098_),
    .DE(net160),
    .Q(_007_),
    .CLK(clknet_2_3__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[12]$_DFFE_PP_  (.D(_099_),
    .DE(net160),
    .Q(_006_),
    .CLK(clknet_2_3__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[13]$_DFFE_PP_  (.D(_100_),
    .DE(net160),
    .Q(_005_),
    .CLK(clknet_2_3__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[14]$_DFFE_PP_  (.D(_101_),
    .DE(net160),
    .Q(_004_),
    .CLK(clknet_2_3__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[15]$_DFFE_PP_  (.D(_039_),
    .DE(net160),
    .Q(_035_),
    .CLK(clknet_2_2__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[1]$_DFFE_PP_  (.D(_088_),
    .DE(net161),
    .Q(_017_),
    .CLK(clknet_2_1__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[2]$_DFFE_PP_  (.D(_089_),
    .DE(net161),
    .Q(_016_),
    .CLK(clknet_2_1__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[3]$_DFFE_PP_  (.D(_090_),
    .DE(net161),
    .Q(_015_),
    .CLK(clknet_2_0__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[4]$_DFFE_PP_  (.D(_091_),
    .DE(net161),
    .Q(_014_),
    .CLK(clknet_2_0__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[5]$_DFFE_PP_  (.D(_092_),
    .DE(net161),
    .Q(_013_),
    .CLK(clknet_2_0__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[6]$_DFFE_PP_  (.D(_093_),
    .DE(net160),
    .Q(_012_),
    .CLK(clknet_2_0__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[7]$_DFFE_PP_  (.D(_094_),
    .DE(net160),
    .Q(_011_),
    .CLK(clknet_2_1__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[8]$_DFFE_PP_  (.D(_095_),
    .DE(net160),
    .Q(_010_),
    .CLK(clknet_2_2__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[9]$_DFFE_PP_  (.D(_096_),
    .DE(net160),
    .Q(_009_),
    .CLK(clknet_2_2__leaf_clk));
 sky130_fd_sc_hd__buf_1 input10 (.A(req_msg[16]),
    .X(net10));
 sky130_fd_sc_hd__buf_1 input11 (.A(req_msg[17]),
    .X(net11));
 sky130_fd_sc_hd__buf_1 input12 (.A(req_msg[18]),
    .X(net12));
 sky130_fd_sc_hd__buf_1 input13 (.A(req_msg[19]),
    .X(net13));
 sky130_fd_sc_hd__buf_1 input14 (.A(req_msg[1]),
    .X(net14));
 sky130_fd_sc_hd__buf_1 input15 (.A(req_msg[20]),
    .X(net15));
 sky130_fd_sc_hd__buf_1 input16 (.A(req_msg[21]),
    .X(net16));
 sky130_fd_sc_hd__buf_1 input17 (.A(req_msg[22]),
    .X(net17));
 sky130_fd_sc_hd__buf_1 input18 (.A(req_msg[23]),
    .X(net18));
 sky130_fd_sc_hd__buf_1 input19 (.A(req_msg[24]),
    .X(net19));
 sky130_fd_sc_hd__buf_1 input20 (.A(req_msg[25]),
    .X(net20));
 sky130_fd_sc_hd__buf_1 input21 (.A(req_msg[26]),
    .X(net21));
 sky130_fd_sc_hd__buf_1 input22 (.A(req_msg[27]),
    .X(net22));
 sky130_fd_sc_hd__buf_1 input23 (.A(req_msg[28]),
    .X(net23));
 sky130_fd_sc_hd__buf_1 input24 (.A(req_msg[29]),
    .X(net24));
 sky130_fd_sc_hd__buf_1 input25 (.A(req_msg[2]),
    .X(net25));
 sky130_fd_sc_hd__buf_1 input26 (.A(req_msg[30]),
    .X(net26));
 sky130_fd_sc_hd__buf_1 input27 (.A(req_msg[31]),
    .X(net27));
 sky130_fd_sc_hd__buf_1 input28 (.A(req_msg[3]),
    .X(net28));
 sky130_fd_sc_hd__buf_1 input29 (.A(req_msg[4]),
    .X(net29));
 sky130_fd_sc_hd__buf_1 input3 (.A(req_msg[0]),
    .X(net3));
 sky130_fd_sc_hd__buf_1 input30 (.A(req_msg[5]),
    .X(net30));
 sky130_fd_sc_hd__buf_1 input31 (.A(req_msg[6]),
    .X(net31));
 sky130_fd_sc_hd__buf_1 input32 (.A(req_msg[7]),
    .X(net32));
 sky130_fd_sc_hd__buf_1 input33 (.A(req_msg[8]),
    .X(net33));
 sky130_fd_sc_hd__buf_1 input34 (.A(req_msg[9]),
    .X(net34));
 sky130_fd_sc_hd__buf_1 input35 (.A(req_val),
    .X(net35));
 sky130_fd_sc_hd__buf_1 input36 (.A(reset),
    .X(net36));
 sky130_fd_sc_hd__buf_1 input37 (.A(resp_rdy),
    .X(net37));
 sky130_fd_sc_hd__buf_1 input4 (.A(req_msg[10]),
    .X(net4));
 sky130_fd_sc_hd__buf_1 input5 (.A(req_msg[11]),
    .X(net5));
 sky130_fd_sc_hd__buf_1 input6 (.A(req_msg[12]),
    .X(net6));
 sky130_fd_sc_hd__buf_1 input7 (.A(req_msg[13]),
    .X(net7));
 sky130_fd_sc_hd__buf_1 input8 (.A(req_msg[14]),
    .X(net8));
 sky130_fd_sc_hd__buf_1 input9 (.A(req_msg[15]),
    .X(net9));
 sky130_fd_sc_hd__buf_1 output38 (.A(net267),
    .X(req_rdy));
 sky130_fd_sc_hd__buf_1 output39 (.A(net39),
    .X(resp_msg[0]));
 sky130_fd_sc_hd__buf_1 output40 (.A(net40),
    .X(resp_msg[10]));
 sky130_fd_sc_hd__buf_1 output41 (.A(net41),
    .X(resp_msg[11]));
 sky130_fd_sc_hd__buf_1 output42 (.A(net163),
    .X(resp_msg[12]));
 sky130_fd_sc_hd__buf_1 output43 (.A(net162),
    .X(resp_msg[13]));
 sky130_fd_sc_hd__buf_1 output44 (.A(net44),
    .X(resp_msg[14]));
 sky130_fd_sc_hd__buf_1 output45 (.A(net169),
    .X(resp_msg[15]));
 sky130_fd_sc_hd__buf_1 output46 (.A(net46),
    .X(resp_msg[1]));
 sky130_fd_sc_hd__buf_1 output47 (.A(net47),
    .X(resp_msg[2]));
 sky130_fd_sc_hd__buf_1 output48 (.A(net177),
    .X(resp_msg[3]));
 sky130_fd_sc_hd__buf_1 output49 (.A(net172),
    .X(resp_msg[4]));
 sky130_fd_sc_hd__buf_1 output50 (.A(net171),
    .X(resp_msg[5]));
 sky130_fd_sc_hd__buf_1 output51 (.A(net170),
    .X(resp_msg[6]));
 sky130_fd_sc_hd__buf_1 output52 (.A(net52),
    .X(resp_msg[7]));
 sky130_fd_sc_hd__buf_1 output53 (.A(net165),
    .X(resp_msg[8]));
 sky130_fd_sc_hd__buf_1 output54 (.A(net164),
    .X(resp_msg[9]));
 sky130_fd_sc_hd__buf_1 output55 (.A(net55),
    .X(resp_val));
 sky130_fd_sc_hd__buf_12 place148 (.A(_038_),
    .X(net160));
 sky130_fd_sc_hd__buf_6 place149 (.A(_038_),
    .X(net161));
 sky130_fd_sc_hd__buf_4 place150 (.A(net43),
    .X(net162));
 sky130_fd_sc_hd__buf_4 place151 (.A(net42),
    .X(net163));
 sky130_fd_sc_hd__buf_4 place152 (.A(net54),
    .X(net164));
 sky130_fd_sc_hd__buf_4 place153 (.A(net53),
    .X(net165));
 sky130_fd_sc_hd__buf_12 place154 (.A(_032_),
    .X(net166));
 sky130_fd_sc_hd__buf_12 place155 (.A(_032_),
    .X(net167));
 sky130_fd_sc_hd__buf_12 place156 (.A(_032_),
    .X(net168));
 sky130_fd_sc_hd__buf_4 place157 (.A(net45),
    .X(net169));
 sky130_fd_sc_hd__buf_4 place158 (.A(net51),
    .X(net170));
 sky130_fd_sc_hd__buf_4 place159 (.A(net50),
    .X(net171));
 sky130_fd_sc_hd__buf_4 place160 (.A(net49),
    .X(net172));
 sky130_fd_sc_hd__buf_4 place165 (.A(net48),
    .X(net177));
 sky130_fd_sc_hd__buf_4 place201 (.A(_107_),
    .X(net213));
 sky130_fd_sc_hd__buf_4 place202 (.A(_105_),
    .X(net214));
 sky130_fd_sc_hd__buf_4 place203 (.A(_104_),
    .X(net215));
 sky130_fd_sc_hd__buf_12 place204 (.A(_041_),
    .X(net216));
 sky130_fd_sc_hd__buf_12 place205 (.A(_041_),
    .X(net217));
 sky130_fd_sc_hd__buf_4 place206 (.A(_040_),
    .X(net218));
 sky130_fd_sc_hd__buf_4 place207 (.A(_040_),
    .X(net219));
 sky130_fd_sc_hd__buf_4 place208 (.A(_040_),
    .X(net220));
 sky130_fd_sc_hd__buf_4 place221 (.A(_009_),
    .X(net233));
 sky130_fd_sc_hd__buf_4 place222 (.A(_010_),
    .X(net234));
 sky130_fd_sc_hd__buf_4 place223 (.A(_010_),
    .X(net236));
 sky130_fd_sc_hd__buf_4 place224 (.A(_011_),
    .X(net237));
 sky130_fd_sc_hd__buf_4 place225 (.A(_012_),
    .X(net238));
 sky130_fd_sc_hd__buf_4 place226 (.A(net301),
    .X(net239));
 sky130_fd_sc_hd__buf_4 place227 (.A(_014_),
    .X(net240));
 sky130_fd_sc_hd__buf_4 place228 (.A(_015_),
    .X(net241));
 sky130_fd_sc_hd__buf_4 place229 (.A(_016_),
    .X(net242));
 sky130_fd_sc_hd__buf_4 place230 (.A(_017_),
    .X(net244));
 sky130_fd_sc_hd__buf_4 place231 (.A(net304),
    .X(net245));
 sky130_fd_sc_hd__buf_4 place232 (.A(_004_),
    .X(net246));
 sky130_fd_sc_hd__buf_4 place233 (.A(_005_),
    .X(net247));
 sky130_fd_sc_hd__buf_4 place234 (.A(_006_),
    .X(net248));
 sky130_fd_sc_hd__buf_4 place235 (.A(_007_),
    .X(net249));
 sky130_fd_sc_hd__buf_4 place236 (.A(_008_),
    .X(net250));
 sky130_fd_sc_hd__buf_4 place237 (.A(_018_),
    .X(net251));
 sky130_fd_sc_hd__buf_4 place238 (.A(_024_),
    .X(net252));
 sky130_fd_sc_hd__buf_4 place239 (.A(_025_),
    .X(net253));
 sky130_fd_sc_hd__buf_4 place241 (.A(_027_),
    .X(net255));
 sky130_fd_sc_hd__buf_4 place242 (.A(_028_),
    .X(net256));
 sky130_fd_sc_hd__buf_4 place243 (.A(_029_),
    .X(net257));
 sky130_fd_sc_hd__buf_4 place244 (.A(_030_),
    .X(net258));
 sky130_fd_sc_hd__buf_4 place245 (.A(_031_),
    .X(net259));
 sky130_fd_sc_hd__buf_4 place246 (.A(_033_),
    .X(net260));
 sky130_fd_sc_hd__buf_4 place247 (.A(_001_),
    .X(net261));
 sky130_fd_sc_hd__buf_4 place248 (.A(_020_),
    .X(net262));
 sky130_fd_sc_hd__buf_4 place249 (.A(net38),
    .X(net264));
 sky130_fd_sc_hd__buf_6 place250 (.A(net280),
    .X(net265));
 sky130_fd_sc_hd__buf_4 place251 (.A(net38),
    .X(net266));
 sky130_fd_sc_hd__buf_6 place252 (.A(net38),
    .X(net267));
 sky130_fd_sc_hd__buf_4 rebuffer_mt265 (.A(net38),
    .X(net280));
 sky130_fd_sc_hd__buf_4 rebuffer_mt286 (.A(_013_),
    .X(net301));
 sky130_fd_sc_hd__buf_4 rebuffer_mt289 (.A(_035_),
    .X(net304));
endmodule
module \ALU_16_0_16_0_16_unused_CO[14:0]_X_KOGGE_STONE  (_020__263,
    _016__243,
    _010__235,
    _001__156,
    _033__154,
    _031__152,
    _030__150,
    _029__148,
    _028__146,
    _027__144,
    _025__140,
    _024__138,
    _014__125,
    _009__119,
    A,
    B,
    BI,
    CI,
    Y,
    \CO[15] );
 input _020__263;
 input _016__243;
 input _010__235;
 input _001__156;
 input _033__154;
 input _031__152;
 input _030__150;
 input _029__148;
 input _028__146;
 input _027__144;
 input _025__140;
 input _024__138;
 input _014__125;
 input _009__119;
 input [15:0] A;
 input [15:0] B;
 input BI;
 input CI;
 output [15:0] Y;
 output \CO[15] ;

 wire _048_;
 wire _047_;
 wire _046_;
 wire _045_;
 wire _044_;
 wire _043_;
 wire _042_;
 wire _041_;
 wire _040_;
 wire _039_;
 wire _038_;
 wire _037_;
 wire _036_;
 wire _034_;
 wire _033_;
 wire _032_;
 wire _031_;
 wire _085_;
 wire _030_;
 wire _035_;
 wire _029_;
 wire _028_;
 wire _027_;
 wire _026_;
 wire _025_;
 wire _024_;
 wire _023_;
 wire _022_;
 wire _021_;
 wire _020_;
 wire _019_;
 wire _018_;
 wire _017_;
 wire _016_;
 wire _015_;
 wire _014_;
 wire _106_;
 wire _013_;
 wire _102_;
 wire _012_;
 wire _011_;
 wire _010_;
 wire _009_;
 wire _008_;
 wire _007_;
 wire _006_;
 wire _119_;
 wire _005_;
 wire _004_;
 wire _003_;
 wire _055_;
 wire _002_;
 wire _127_;
 wire _126_;
 wire _110_;
 wire _091_;
 wire _001_;
 wire _125_;
 wire _114_;
 wire _000_;
 wire _057_;
 wire _061_;
 wire _058_;
 wire _049_;
 wire _050_;
 wire _051_;
 wire _052_;
 wire _053_;
 wire _054_;
 wire _056_;
 wire _059_;
 wire _060_;
 wire _062_;
 wire _063_;
 wire _064_;
 wire _065_;
 wire _066_;
 wire _067_;
 wire _068_;
 wire _069_;
 wire _070_;
 wire _071_;
 wire _072_;
 wire _073_;
 wire _074_;
 wire _075_;
 wire _076_;
 wire _077_;
 wire _078_;
 wire _079_;
 wire _080_;
 wire _081_;
 wire _082_;
 wire _083_;
 wire _084_;
 wire _086_;
 wire _087_;
 wire _088_;
 wire _089_;
 wire _090_;
 wire _092_;
 wire _093_;
 wire _094_;
 wire _095_;
 wire _096_;
 wire _097_;
 wire _098_;
 wire _099_;
 wire _100_;
 wire _101_;
 wire _103_;
 wire _104_;
 wire _105_;
 wire _107_;
 wire _108_;
 wire _109_;
 wire _111_;
 wire _112_;
 wire _113_;
 wire _115_;
 wire _116_;
 wire _117_;
 wire _118_;
 wire _120_;
 wire _121_;
 wire _122_;
 wire _123_;
 wire _124_;
 wire net186;
 wire net175;
 wire net173;
 wire net174;
 wire net176;
 wire net185;
 wire net178;
 wire net179;
 wire net180;
 wire net181;
 wire net182;
 wire net183;
 wire net184;
 wire net187;
 wire net188;
 wire net189;
 wire net190;
 wire net191;
 wire net192;
 wire net193;
 wire net195;
 wire net196;
 wire net198;
 wire net199;
 wire net200;
 wire net201;
 wire net202;
 wire net203;
 wire net206;
 wire net207;
 wire net209;
 wire net210;
 wire net211;
 wire net212;
 wire net226;
 wire net223;
 wire net221;
 wire net222;
 wire net224;
 wire net225;
 wire net227;
 wire net228;
 wire net229;
 wire net230;
 wire net231;
 wire net232;
 wire net254;
 wire net194;
 wire net197;
 wire net204;
 wire net205;
 wire net208;
 wire net268;
 wire net269;
 wire net281;
 wire net282;
 wire net283;
 wire net284;
 wire net285;
 wire net286;
 wire net294;
 wire net297;
 wire net299;
 wire net300;
 wire net308;

 sky130_fd_sc_hd__o21ai_0 _128_ (.A1(net201),
    .A2(_061_),
    .B1(_057_),
    .Y(_000_));
 sky130_fd_sc_hd__a21oi_1 _129_ (.A1(_114_),
    .A2(_125_),
    .B1(_000_),
    .Y(_001_));
 sky130_fd_sc_hd__o311ai_2 _130_ (.A1(_126_),
    .A2(_110_),
    .A3(_091_),
    .B1(_127_),
    .C1(_001_),
    .Y(_002_));
 sky130_fd_sc_hd__xnor2_2 _131_ (.A(net202),
    .B(_002_),
    .Y(Y[15]));
 sky130_fd_sc_hd__xor2_2 _132_ (.A(BI),
    .B(B[6]),
    .X(_003_));
 sky130_fd_sc_hd__nand2_1 _133_ (.A(_027__144),
    .B(net232),
    .Y(_004_));
 sky130_fd_sc_hd__xnor2_2 _134_ (.A(A[6]),
    .B(_003_),
    .Y(_005_));
 sky130_fd_sc_hd__nor2_2 _135_ (.A(_119_),
    .B(_005_),
    .Y(_006_));
 sky130_fd_sc_hd__xor2_1 _136_ (.A(B[5]),
    .B(BI),
    .X(_007_));
 sky130_fd_sc_hd__nand2_1 _137_ (.A(_028__146),
    .B(net231),
    .Y(_008_));
 sky130_fd_sc_hd__xor2_1 _138_ (.A(_014__125),
    .B(BI),
    .X(_009_));
 sky130_fd_sc_hd__nand2_1 _139_ (.A(_029__148),
    .B(_009_),
    .Y(_010_));
 sky130_fd_sc_hd__xnor2_4 _140_ (.A(A[5]),
    .B(net299),
    .Y(_011_));
 sky130_fd_sc_hd__o21ai_2 _141_ (.A1(_010_),
    .A2(_011_),
    .B1(_008_),
    .Y(_012_));
 sky130_fd_sc_hd__o211ai_1 _142_ (.A1(A[7]),
    .A2(net221),
    .B1(net232),
    .C1(_027__144),
    .Y(_013_));
 sky130_fd_sc_hd__nand2_1 _143_ (.A(_106_),
    .B(_013_),
    .Y(_014_));
 sky130_fd_sc_hd__a21oi_4 _144_ (.A1(_006_),
    .A2(net196),
    .B1(_014_),
    .Y(_015_));
 sky130_fd_sc_hd__xnor3_2 _145_ (.A(A[4]),
    .B(BI),
    .C(B[4]),
    .X(_016_));
 sky130_fd_sc_hd__nor2_1 _146_ (.A(_011_),
    .B(_016_),
    .Y(_017_));
 sky130_fd_sc_hd__nand2_2 _147_ (.A(_006_),
    .B(net195),
    .Y(_018_));
 sky130_fd_sc_hd__xor2_1 _148_ (.A(B[3]),
    .B(BI),
    .X(_019_));
 sky130_fd_sc_hd__nand2_1 _149_ (.A(_030__150),
    .B(_019_),
    .Y(_020_));
 sky130_fd_sc_hd__xnor3_2 _150_ (.A(A[3]),
    .B(BI),
    .C(B[3]),
    .X(_021_));
 sky130_fd_sc_hd__xor2_1 _151_ (.A(BI),
    .B(B[2]),
    .X(_022_));
 sky130_fd_sc_hd__nand2_1 _152_ (.A(_031__152),
    .B(_022_),
    .Y(_023_));
 sky130_fd_sc_hd__xor3_1 _153_ (.A(A[2]),
    .B(BI),
    .C(_016__243),
    .X(_024_));
 sky130_fd_sc_hd__xnor2_1 _154_ (.A(_031__152),
    .B(_022_),
    .Y(_025_));
 sky130_fd_sc_hd__nor2_1 _155_ (.A(net209),
    .B(_021_),
    .Y(_026_));
 sky130_fd_sc_hd__xor2_1 _156_ (.A(B[1]),
    .B(BI),
    .X(_027_));
 sky130_fd_sc_hd__nand2_1 _157_ (.A(_033__154),
    .B(_027_),
    .Y(_028_));
 sky130_fd_sc_hd__xnor2_1 _158_ (.A(BI),
    .B(B[0]),
    .Y(_029_));
 sky130_fd_sc_hd__xnor2_2 _159_ (.A(net227),
    .B(net229),
    .Y(_030_));
 sky130_fd_sc_hd__maj3_2 _160_ (.A(_035_),
    .B(_029_),
    .C(_085_),
    .X(_031_));
 sky130_fd_sc_hd__nor2_1 _161_ (.A(_033__154),
    .B(_027_),
    .Y(_032_));
 sky130_fd_sc_hd__xor3_1 _162_ (.A(A[1]),
    .B(BI),
    .C(B[1]),
    .X(_033_));
 sky130_fd_sc_hd__o21ai_4 _163_ (.A1(_032_),
    .A2(_031_),
    .B1(_028_),
    .Y(_034_));
 sky130_fd_sc_hd__clkinv_1 _164_ (.A(A[0]),
    .Y(_035_));
 sky130_fd_sc_hd__o21ai_2 _165_ (.A1(_023_),
    .A2(_021_),
    .B1(_020_),
    .Y(_036_));
 sky130_fd_sc_hd__a21oi_2 _166_ (.A1(_034_),
    .A2(_026_),
    .B1(net193),
    .Y(_037_));
 sky130_fd_sc_hd__o21ai_2 _167_ (.A1(_018_),
    .A2(_037_),
    .B1(_015_),
    .Y(_038_));
 sky130_fd_sc_hd__xor2_1 _168_ (.A(BI),
    .B(B[11]),
    .X(_039_));
 sky130_fd_sc_hd__nand2_1 _169_ (.A(A[11]),
    .B(_039_),
    .Y(_040_));
 sky130_fd_sc_hd__xnor2_2 _170_ (.A(A[11]),
    .B(_039_),
    .Y(_041_));
 sky130_fd_sc_hd__xor2_1 _171_ (.A(BI),
    .B(B[10]),
    .X(_042_));
 sky130_fd_sc_hd__nand2_1 _172_ (.A(A[10]),
    .B(_042_),
    .Y(_043_));
 sky130_fd_sc_hd__xnor2_2 _173_ (.A(A[10]),
    .B(_042_),
    .Y(_044_));
 sky130_fd_sc_hd__nor2_2 _174_ (.A(_041_),
    .B(_044_),
    .Y(_045_));
 sky130_fd_sc_hd__xor2_1 _175_ (.A(_009__119),
    .B(BI),
    .X(_046_));
 sky130_fd_sc_hd__nand2_1 _176_ (.A(_024__138),
    .B(_046_),
    .Y(_047_));
 sky130_fd_sc_hd__xnor3_1 _177_ (.A(BI),
    .B(B[9]),
    .C(A[9]),
    .X(_048_));
 sky130_fd_sc_hd__xor2_1 _178_ (.A(_010__235),
    .B(BI),
    .X(_049_));
 sky130_fd_sc_hd__nand2_1 _179_ (.A(_025__140),
    .B(_049_),
    .Y(_050_));
 sky130_fd_sc_hd__xnor3_1 _180_ (.A(A[8]),
    .B(B[8]),
    .C(BI),
    .X(_051_));
 sky130_fd_sc_hd__nor2_2 _181_ (.A(_048_),
    .B(_051_),
    .Y(_052_));
 sky130_fd_sc_hd__nand2_1 _182_ (.A(_045_),
    .B(_052_),
    .Y(_053_));
 sky130_fd_sc_hd__xor2_2 _183_ (.A(B[15]),
    .B(BI),
    .X(_054_));
 sky130_fd_sc_hd__xnor2_2 _184_ (.A(A[15]),
    .B(_054_),
    .Y(_055_));
 sky130_fd_sc_hd__xor2_1 _185_ (.A(BI),
    .B(B[14]),
    .X(_056_));
 sky130_fd_sc_hd__nand2_1 _186_ (.A(A[14]),
    .B(net222),
    .Y(_057_));
 sky130_fd_sc_hd__xnor2_1 _187_ (.A(A[14]),
    .B(net286),
    .Y(_058_));
 sky130_fd_sc_hd__nor2_2 _188_ (.A(_058_),
    .B(_055_),
    .Y(_059_));
 sky130_fd_sc_hd__xor2_1 _189_ (.A(BI),
    .B(B[13]),
    .X(_060_));
 sky130_fd_sc_hd__nand2_1 _190_ (.A(_020__263),
    .B(net282),
    .Y(_061_));
 sky130_fd_sc_hd__xnor2_2 _191_ (.A(A[13]),
    .B(net283),
    .Y(_062_));
 sky130_fd_sc_hd__xor2_1 _192_ (.A(B[12]),
    .B(BI),
    .X(_063_));
 sky130_fd_sc_hd__nand2_1 _193_ (.A(A[12]),
    .B(_063_),
    .Y(_064_));
 sky130_fd_sc_hd__xnor2_1 _194_ (.A(A[12]),
    .B(_063_),
    .Y(_065_));
 sky130_fd_sc_hd__nor2_1 _195_ (.A(net269),
    .B(_065_),
    .Y(_066_));
 sky130_fd_sc_hd__nand2_4 _196_ (.A(net191),
    .B(_066_),
    .Y(_067_));
 sky130_fd_sc_hd__nor2_1 _197_ (.A(_053_),
    .B(_067_),
    .Y(_068_));
 sky130_fd_sc_hd__nor2_1 _198_ (.A(_055_),
    .B(_057_),
    .Y(_069_));
 sky130_fd_sc_hd__o21ai_2 _199_ (.A1(_064_),
    .A2(_062_),
    .B1(_061_),
    .Y(_070_));
 sky130_fd_sc_hd__o21ai_1 _200_ (.A1(_048_),
    .A2(_050_),
    .B1(_047_),
    .Y(_071_));
 sky130_fd_sc_hd__o21ai_1 _201_ (.A1(_041_),
    .A2(_043_),
    .B1(_040_),
    .Y(_072_));
 sky130_fd_sc_hd__a21oi_2 _202_ (.A1(_071_),
    .A2(_045_),
    .B1(_072_),
    .Y(_073_));
 sky130_fd_sc_hd__a221oi_4 _203_ (.A1(_001__156),
    .A2(net223),
    .B1(_059_),
    .B2(_070_),
    .C1(_069_),
    .Y(_074_));
 sky130_fd_sc_hd__o21ai_2 _204_ (.A1(_067_),
    .A2(_073_),
    .B1(_074_),
    .Y(_075_));
 sky130_fd_sc_hd__a21o_4 _205_ (.A1(_038_),
    .A2(_068_),
    .B1(_075_),
    .X(\CO[15] ));
 sky130_fd_sc_hd__xnor2_1 _206_ (.A(CI),
    .B(_030_),
    .Y(Y[0]));
 sky130_fd_sc_hd__xnor2_2 _207_ (.A(net208),
    .B(net228),
    .Y(Y[1]));
 sky130_fd_sc_hd__xnor2_2 _208_ (.A(net209),
    .B(net194),
    .Y(Y[2]));
 sky130_fd_sc_hd__nand2_2 _209_ (.A(_033_),
    .B(_024_),
    .Y(_076_));
 sky130_fd_sc_hd__nand3_2 _210_ (.A(_033__154),
    .B(_024_),
    .C(_027_),
    .Y(_077_));
 sky130_fd_sc_hd__o211ai_2 _211_ (.A1(_031_),
    .A2(_076_),
    .B1(_077_),
    .C1(net210),
    .Y(_078_));
 sky130_fd_sc_hd__xnor2_1 _212_ (.A(_021_),
    .B(net187),
    .Y(Y[3]));
 sky130_fd_sc_hd__xor2_2 _213_ (.A(net230),
    .B(net180),
    .X(Y[4]));
 sky130_fd_sc_hd__or2_4 _214_ (.A(_016_),
    .B(_021_),
    .X(_079_));
 sky130_fd_sc_hd__o21ai_1 _215_ (.A1(_016_),
    .A2(_020_),
    .B1(_010_),
    .Y(_080_));
 sky130_fd_sc_hd__nor3_2 _216_ (.A(_031_),
    .B(_076_),
    .C(_079_),
    .Y(_081_));
 sky130_fd_sc_hd__a21oi_2 _217_ (.A1(net210),
    .A2(net294),
    .B1(_079_),
    .Y(_082_));
 sky130_fd_sc_hd__nor3_2 _218_ (.A(_080_),
    .B(net186),
    .C(net185),
    .Y(_083_));
 sky130_fd_sc_hd__xor2_2 _219_ (.A(net300),
    .B(_083_),
    .X(Y[5]));
 sky130_fd_sc_hd__nor4_1 _220_ (.A(_011_),
    .B(_016_),
    .C(_021_),
    .D(net284),
    .Y(_084_));
 sky130_fd_sc_hd__clkinv_1 _221_ (.A(CI),
    .Y(_085_));
 sky130_fd_sc_hd__a221oi_1 _222_ (.A1(_017_),
    .A2(_036_),
    .B1(_084_),
    .B2(_034_),
    .C1(_012_),
    .Y(_086_));
 sky130_fd_sc_hd__xor2_1 _223_ (.A(net212),
    .B(net176),
    .X(Y[6]));
 sky130_fd_sc_hd__nor2_1 _224_ (.A(_005_),
    .B(net211),
    .Y(_087_));
 sky130_fd_sc_hd__nor3_2 _225_ (.A(_005_),
    .B(net211),
    .C(_079_),
    .Y(_088_));
 sky130_fd_sc_hd__o211ai_1 _226_ (.A1(_027__144),
    .A2(net232),
    .B1(net231),
    .C1(_028__146),
    .Y(_089_));
 sky130_fd_sc_hd__nand2_1 _227_ (.A(_004_),
    .B(_089_),
    .Y(_090_));
 sky130_fd_sc_hd__a221oi_2 _228_ (.A1(_080_),
    .A2(_087_),
    .B1(_078_),
    .B2(_088_),
    .C1(_090_),
    .Y(_091_));
 sky130_fd_sc_hd__xor2_4 _229_ (.A(net198),
    .B(net175),
    .X(Y[7]));
 sky130_fd_sc_hd__xnor2_2 _230_ (.A(net173),
    .B(net224),
    .Y(Y[8]));
 sky130_fd_sc_hd__nor2_1 _231_ (.A(net198),
    .B(net224),
    .Y(_092_));
 sky130_fd_sc_hd__a211oi_1 _232_ (.A1(_004_),
    .A2(_089_),
    .B1(net224),
    .C1(_119_),
    .Y(_093_));
 sky130_fd_sc_hd__o211ai_1 _233_ (.A1(_025__140),
    .A2(net225),
    .B1(net221),
    .C1(net254),
    .Y(_094_));
 sky130_fd_sc_hd__nand2_1 _234_ (.A(net204),
    .B(_094_),
    .Y(_095_));
 sky130_fd_sc_hd__nor2_1 _235_ (.A(net184),
    .B(_095_),
    .Y(_096_));
 sky130_fd_sc_hd__nor4_1 _236_ (.A(_119_),
    .B(_005_),
    .C(net211),
    .D(net224),
    .Y(_097_));
 sky130_fd_sc_hd__o31ai_1 _237_ (.A1(_080_),
    .A2(_082_),
    .A3(_081_),
    .B1(_097_),
    .Y(_098_));
 sky130_fd_sc_hd__nand2_2 _238_ (.A(_096_),
    .B(net174),
    .Y(_099_));
 sky130_fd_sc_hd__xnor2_2 _239_ (.A(net226),
    .B(_099_),
    .Y(Y[9]));
 sky130_fd_sc_hd__a21boi_0 _240_ (.A1(_106_),
    .A2(_013_),
    .B1_N(_052_),
    .Y(_100_));
 sky130_fd_sc_hd__nor2_1 _241_ (.A(net188),
    .B(_100_),
    .Y(_101_));
 sky130_fd_sc_hd__xor2_2 _242_ (.A(BI),
    .B(B[7]),
    .X(_102_));
 sky130_fd_sc_hd__nand2_1 _243_ (.A(net197),
    .B(net203),
    .Y(_103_));
 sky130_fd_sc_hd__o21ai_2 _244_ (.A1(net268),
    .A2(_103_),
    .B1(_101_),
    .Y(_104_));
 sky130_fd_sc_hd__xnor2_2 _245_ (.A(net205),
    .B(_104_),
    .Y(Y[10]));
 sky130_fd_sc_hd__nor2_1 _246_ (.A(net205),
    .B(net226),
    .Y(_105_));
 sky130_fd_sc_hd__nand2_1 _247_ (.A(net254),
    .B(net221),
    .Y(_106_));
 sky130_fd_sc_hd__a211oi_1 _248_ (.A1(net204),
    .A2(_094_),
    .B1(net205),
    .C1(net226),
    .Y(_107_));
 sky130_fd_sc_hd__o21ai_0 _249_ (.A1(net205),
    .A2(_047_),
    .B1(_043_),
    .Y(_108_));
 sky130_fd_sc_hd__nor2_1 _250_ (.A(_107_),
    .B(_108_),
    .Y(_109_));
 sky130_fd_sc_hd__nand2_1 _251_ (.A(_092_),
    .B(_105_),
    .Y(_110_));
 sky130_fd_sc_hd__o21ai_1 _252_ (.A1(_110_),
    .A2(_091_),
    .B1(_109_),
    .Y(_111_));
 sky130_fd_sc_hd__xnor2_1 _253_ (.A(net206),
    .B(_111_),
    .Y(Y[11]));
 sky130_fd_sc_hd__nand4_1 _254_ (.A(net197),
    .B(net195),
    .C(net192),
    .D(_052_),
    .Y(_112_));
 sky130_fd_sc_hd__o221ai_2 _255_ (.A1(net181),
    .A2(net179),
    .B1(_112_),
    .B2(net180),
    .C1(net178),
    .Y(_113_));
 sky130_fd_sc_hd__xnor2_2 _256_ (.A(net199),
    .B(_113_),
    .Y(Y[12]));
 sky130_fd_sc_hd__o21ai_0 _257_ (.A1(net207),
    .A2(_065_),
    .B1(_064_),
    .Y(_114_));
 sky130_fd_sc_hd__nor2_1 _258_ (.A(net206),
    .B(_065_),
    .Y(_115_));
 sky130_fd_sc_hd__nand2_1 _259_ (.A(net183),
    .B(net182),
    .Y(_116_));
 sky130_fd_sc_hd__o211ai_1 _260_ (.A1(net184),
    .A2(_095_),
    .B1(net183),
    .C1(net182),
    .Y(_117_));
 sky130_fd_sc_hd__a21oi_1 _261_ (.A1(_108_),
    .A2(_115_),
    .B1(_114_),
    .Y(_118_));
 sky130_fd_sc_hd__xnor2_2 _262_ (.A(A[7]),
    .B(_102_),
    .Y(_119_));
 sky130_fd_sc_hd__o211ai_2 _263_ (.A1(_116_),
    .A2(net174),
    .B1(_117_),
    .C1(_118_),
    .Y(_120_));
 sky130_fd_sc_hd__xnor2_1 _264_ (.A(net200),
    .B(_120_),
    .Y(Y[13]));
 sky130_fd_sc_hd__nand4_1 _265_ (.A(net197),
    .B(net192),
    .C(net203),
    .D(net190),
    .Y(_121_));
 sky130_fd_sc_hd__o211ai_1 _266_ (.A1(net188),
    .A2(_100_),
    .B1(net192),
    .C1(net190),
    .Y(_122_));
 sky130_fd_sc_hd__a21oi_1 _267_ (.A1(net190),
    .A2(_072_),
    .B1(net189),
    .Y(_123_));
 sky130_fd_sc_hd__o211ai_2 _268_ (.A1(_121_),
    .A2(net268),
    .B1(_122_),
    .C1(_123_),
    .Y(_124_));
 sky130_fd_sc_hd__xnor2_1 _269_ (.A(net201),
    .B(_124_),
    .Y(Y[14]));
 sky130_fd_sc_hd__nor2_1 _270_ (.A(net201),
    .B(net269),
    .Y(_125_));
 sky130_fd_sc_hd__nand2_1 _271_ (.A(_115_),
    .B(_125_),
    .Y(_126_));
 sky130_fd_sc_hd__o211ai_1 _272_ (.A1(_107_),
    .A2(_108_),
    .B1(net182),
    .C1(_125_),
    .Y(_127_));
 sky130_fd_sc_hd__buf_6 place161 (.A(net297),
    .X(net173));
 sky130_fd_sc_hd__buf_6 place162 (.A(_098_),
    .X(net174));
 sky130_fd_sc_hd__buf_4 place163 (.A(_091_),
    .X(net175));
 sky130_fd_sc_hd__buf_6 place164 (.A(net268),
    .X(net176));
 sky130_fd_sc_hd__buf_4 place166 (.A(_073_),
    .X(net178));
 sky130_fd_sc_hd__buf_4 place167 (.A(_053_),
    .X(net179));
 sky130_fd_sc_hd__buf_4 place168 (.A(_037_),
    .X(net180));
 sky130_fd_sc_hd__buf_4 place169 (.A(_015_),
    .X(net181));
 sky130_fd_sc_hd__buf_4 place170 (.A(_115_),
    .X(net182));
 sky130_fd_sc_hd__buf_4 place171 (.A(_105_),
    .X(net183));
 sky130_fd_sc_hd__buf_4 place172 (.A(_093_),
    .X(net184));
 sky130_fd_sc_hd__buf_4 place173 (.A(_082_),
    .X(net185));
 sky130_fd_sc_hd__buf_4 place174 (.A(_081_),
    .X(net186));
 sky130_fd_sc_hd__buf_6 place175 (.A(_078_),
    .X(net187));
 sky130_fd_sc_hd__buf_4 place176 (.A(_071_),
    .X(net188));
 sky130_fd_sc_hd__buf_4 place177 (.A(_070_),
    .X(net189));
 sky130_fd_sc_hd__buf_4 place178 (.A(_066_),
    .X(net190));
 sky130_fd_sc_hd__buf_4 place179 (.A(_059_),
    .X(net191));
 sky130_fd_sc_hd__buf_4 place180 (.A(_045_),
    .X(net192));
 sky130_fd_sc_hd__buf_6 place181 (.A(_036_),
    .X(net193));
 sky130_fd_sc_hd__buf_4 place182 (.A(_034_),
    .X(net194));
 sky130_fd_sc_hd__buf_4 place183 (.A(_017_),
    .X(net195));
 sky130_fd_sc_hd__buf_6 place184 (.A(_012_),
    .X(net196));
 sky130_fd_sc_hd__buf_4 place185 (.A(_006_),
    .X(net197));
 sky130_fd_sc_hd__buf_4 place186 (.A(_119_),
    .X(net198));
 sky130_fd_sc_hd__buf_4 place187 (.A(_065_),
    .X(net199));
 sky130_fd_sc_hd__buf_4 place188 (.A(net269),
    .X(net200));
 sky130_fd_sc_hd__buf_4 place189 (.A(_058_),
    .X(net201));
 sky130_fd_sc_hd__buf_4 place190 (.A(net308),
    .X(net202));
 sky130_fd_sc_hd__buf_4 place191 (.A(_052_),
    .X(net203));
 sky130_fd_sc_hd__buf_4 place192 (.A(_050_),
    .X(net204));
 sky130_fd_sc_hd__buf_4 place193 (.A(_044_),
    .X(net205));
 sky130_fd_sc_hd__buf_4 place194 (.A(_041_),
    .X(net206));
 sky130_fd_sc_hd__buf_4 place195 (.A(_040_),
    .X(net207));
 sky130_fd_sc_hd__buf_4 place196 (.A(_031_),
    .X(net208));
 sky130_fd_sc_hd__buf_4 place197 (.A(_025_),
    .X(net209));
 sky130_fd_sc_hd__buf_4 place198 (.A(_023_),
    .X(net210));
 sky130_fd_sc_hd__buf_8 place199 (.A(_011_),
    .X(net211));
 sky130_fd_sc_hd__buf_4 place200 (.A(_005_),
    .X(net212));
 sky130_fd_sc_hd__buf_4 place209 (.A(_102_),
    .X(net221));
 sky130_fd_sc_hd__buf_4 place210 (.A(net285),
    .X(net222));
 sky130_fd_sc_hd__buf_4 place211 (.A(net281),
    .X(net223));
 sky130_fd_sc_hd__buf_4 place212 (.A(_051_),
    .X(net224));
 sky130_fd_sc_hd__buf_4 place213 (.A(_049_),
    .X(net225));
 sky130_fd_sc_hd__buf_4 place214 (.A(_048_),
    .X(net226));
 sky130_fd_sc_hd__buf_4 place215 (.A(_035_),
    .X(net227));
 sky130_fd_sc_hd__buf_4 place216 (.A(_033_),
    .X(net228));
 sky130_fd_sc_hd__buf_4 place217 (.A(_029_),
    .X(net229));
 sky130_fd_sc_hd__buf_4 place218 (.A(_016_),
    .X(net230));
 sky130_fd_sc_hd__buf_4 place219 (.A(net299),
    .X(net231));
 sky130_fd_sc_hd__buf_4 place220 (.A(_003_),
    .X(net232));
 sky130_fd_sc_hd__buf_4 place240 (.A(A[7]),
    .X(net254));
 sky130_fd_sc_hd__buf_6 rebuffer_mt253 (.A(_086_),
    .X(net268));
 sky130_fd_sc_hd__buf_4 rebuffer_mt254 (.A(_062_),
    .X(net269));
 sky130_fd_sc_hd__buf_4 rebuffer_mt266 (.A(_054_),
    .X(net281));
 sky130_fd_sc_hd__buf_4 rebuffer_mt267 (.A(net283),
    .X(net282));
 sky130_fd_sc_hd__buf_4 rebuffer_mt268 (.A(_060_),
    .X(net283));
 sky130_fd_sc_hd__buf_4 rebuffer_mt269 (.A(_025_),
    .X(net284));
 sky130_fd_sc_hd__buf_4 rebuffer_mt270 (.A(net286),
    .X(net285));
 sky130_fd_sc_hd__buf_4 rebuffer_mt271 (.A(_056_),
    .X(net286));
 sky130_fd_sc_hd__buf_4 rebuffer_mt279 (.A(_077_),
    .X(net294));
 sky130_fd_sc_hd__buf_4 rebuffer_mt282 (.A(_038_),
    .X(net297));
 sky130_fd_sc_hd__buf_4 rebuffer_mt284 (.A(_007_),
    .X(net299));
 sky130_fd_sc_hd__buf_4 rebuffer_mt285 (.A(net211),
    .X(net300));
 sky130_fd_sc_hd__buf_4 rebuffer_mt293 (.A(_055_),
    .X(net308));
endmodule
