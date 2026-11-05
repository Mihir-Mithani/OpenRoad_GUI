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

 wire _032_;
 wire _000_;
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

 \ALU_16_0_16_0_16_unused_CO[14:0]_X_HAN_CARLSON  _119_ (.A({_001_,
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
    .BI(_000_),
    .CI(_000_),
    .Y({resp_msg[15],
    resp_msg[14],
    resp_msg[13],
    resp_msg[12],
    resp_msg[11],
    resp_msg[10],
    resp_msg[9],
    resp_msg[8],
    resp_msg[7],
    resp_msg[6],
    resp_msg[5],
    resp_msg[4],
    resp_msg[3],
    resp_msg[2],
    resp_msg[1],
    resp_msg[0]}),
    .\CO[15] (_032_));
 sky130_fd_sc_hd__conb_1 _120_ (.HI(_000_));
 sky130_fd_sc_hd__clkinv_1 _121_ (.A(_003_),
    .Y(_036_));
 sky130_fd_sc_hd__clkinv_1 _122_ (.A(_002_),
    .Y(_037_));
 sky130_fd_sc_hd__o21bai_1 _123_ (.A1(_037_),
    .A2(_032_),
    .B1_N(req_rdy),
    .Y(_038_));
 sky130_fd_sc_hd__mux2_1 _124_ (.A0(_001_),
    .A1(req_msg[15]),
    .S(req_rdy),
    .X(_039_));
 sky130_fd_sc_hd__or2_0 _125_ (.A(req_rdy),
    .B(_002_),
    .X(_040_));
 sky130_fd_sc_hd__nand2b_1 _126_ (.A_N(req_rdy),
    .B(_002_),
    .Y(_041_));
 sky130_fd_sc_hd__mux2i_1 _127_ (.A0(_018_),
    .A1(resp_msg[0]),
    .S(_032_),
    .Y(_042_));
 sky130_fd_sc_hd__nand2_1 _128_ (.A(req_msg[16]),
    .B(_041_),
    .Y(_043_));
 sky130_fd_sc_hd__o21ai_0 _129_ (.A1(_041_),
    .A2(_042_),
    .B1(_043_),
    .Y(_044_));
 sky130_fd_sc_hd__mux2i_1 _130_ (.A0(_017_),
    .A1(resp_msg[1]),
    .S(_032_),
    .Y(_045_));
 sky130_fd_sc_hd__nand2_1 _131_ (.A(req_msg[17]),
    .B(_041_),
    .Y(_046_));
 sky130_fd_sc_hd__o21ai_0 _132_ (.A1(_041_),
    .A2(_045_),
    .B1(_046_),
    .Y(_047_));
 sky130_fd_sc_hd__mux2i_1 _133_ (.A0(_016_),
    .A1(resp_msg[2]),
    .S(_032_),
    .Y(_048_));
 sky130_fd_sc_hd__nand2_1 _134_ (.A(req_msg[18]),
    .B(_041_),
    .Y(_049_));
 sky130_fd_sc_hd__o21ai_0 _135_ (.A1(_041_),
    .A2(_048_),
    .B1(_049_),
    .Y(_050_));
 sky130_fd_sc_hd__mux2i_1 _136_ (.A0(_015_),
    .A1(resp_msg[3]),
    .S(_032_),
    .Y(_051_));
 sky130_fd_sc_hd__nand2_1 _137_ (.A(req_msg[19]),
    .B(_041_),
    .Y(_052_));
 sky130_fd_sc_hd__o21ai_0 _138_ (.A1(_041_),
    .A2(_051_),
    .B1(_052_),
    .Y(_053_));
 sky130_fd_sc_hd__mux2i_1 _139_ (.A0(_014_),
    .A1(resp_msg[4]),
    .S(_032_),
    .Y(_054_));
 sky130_fd_sc_hd__nand2_1 _140_ (.A(req_msg[20]),
    .B(_041_),
    .Y(_055_));
 sky130_fd_sc_hd__o21ai_0 _141_ (.A1(_041_),
    .A2(_054_),
    .B1(_055_),
    .Y(_056_));
 sky130_fd_sc_hd__mux2i_1 _142_ (.A0(_013_),
    .A1(resp_msg[5]),
    .S(_032_),
    .Y(_057_));
 sky130_fd_sc_hd__nand2_1 _143_ (.A(req_msg[21]),
    .B(_041_),
    .Y(_058_));
 sky130_fd_sc_hd__o21ai_0 _144_ (.A1(_041_),
    .A2(_057_),
    .B1(_058_),
    .Y(_059_));
 sky130_fd_sc_hd__mux2i_1 _145_ (.A0(_012_),
    .A1(resp_msg[6]),
    .S(_032_),
    .Y(_060_));
 sky130_fd_sc_hd__nand2_1 _146_ (.A(req_msg[22]),
    .B(_041_),
    .Y(_061_));
 sky130_fd_sc_hd__o21ai_0 _147_ (.A1(_041_),
    .A2(_060_),
    .B1(_061_),
    .Y(_062_));
 sky130_fd_sc_hd__mux2i_1 _148_ (.A0(_011_),
    .A1(resp_msg[7]),
    .S(_032_),
    .Y(_063_));
 sky130_fd_sc_hd__nand2_1 _149_ (.A(req_msg[23]),
    .B(_041_),
    .Y(_064_));
 sky130_fd_sc_hd__o21ai_0 _150_ (.A1(_041_),
    .A2(_063_),
    .B1(_064_),
    .Y(_065_));
 sky130_fd_sc_hd__mux2i_1 _151_ (.A0(_010_),
    .A1(resp_msg[8]),
    .S(_032_),
    .Y(_066_));
 sky130_fd_sc_hd__nand2_1 _152_ (.A(req_msg[24]),
    .B(_041_),
    .Y(_067_));
 sky130_fd_sc_hd__o21ai_0 _153_ (.A1(_041_),
    .A2(_066_),
    .B1(_067_),
    .Y(_068_));
 sky130_fd_sc_hd__mux2i_1 _154_ (.A0(_009_),
    .A1(resp_msg[9]),
    .S(_032_),
    .Y(_069_));
 sky130_fd_sc_hd__nand2_1 _155_ (.A(req_msg[25]),
    .B(_041_),
    .Y(_070_));
 sky130_fd_sc_hd__o21ai_0 _156_ (.A1(_041_),
    .A2(_069_),
    .B1(_070_),
    .Y(_071_));
 sky130_fd_sc_hd__mux2i_1 _157_ (.A0(_008_),
    .A1(resp_msg[10]),
    .S(_032_),
    .Y(_072_));
 sky130_fd_sc_hd__nand2_1 _158_ (.A(req_msg[26]),
    .B(_041_),
    .Y(_073_));
 sky130_fd_sc_hd__o21ai_0 _159_ (.A1(_041_),
    .A2(_072_),
    .B1(_073_),
    .Y(_074_));
 sky130_fd_sc_hd__mux2i_1 _160_ (.A0(_007_),
    .A1(resp_msg[11]),
    .S(_032_),
    .Y(_075_));
 sky130_fd_sc_hd__nand2_1 _161_ (.A(req_msg[27]),
    .B(_041_),
    .Y(_076_));
 sky130_fd_sc_hd__o21ai_0 _162_ (.A1(_041_),
    .A2(_075_),
    .B1(_076_),
    .Y(_077_));
 sky130_fd_sc_hd__mux2i_1 _163_ (.A0(_006_),
    .A1(resp_msg[12]),
    .S(_032_),
    .Y(_078_));
 sky130_fd_sc_hd__nand2_1 _164_ (.A(req_msg[28]),
    .B(_041_),
    .Y(_079_));
 sky130_fd_sc_hd__o21ai_0 _165_ (.A1(_041_),
    .A2(_078_),
    .B1(_079_),
    .Y(_080_));
 sky130_fd_sc_hd__mux2i_1 _166_ (.A0(_005_),
    .A1(resp_msg[13]),
    .S(_032_),
    .Y(_081_));
 sky130_fd_sc_hd__nand2_1 _167_ (.A(req_msg[29]),
    .B(_041_),
    .Y(_082_));
 sky130_fd_sc_hd__o21ai_0 _168_ (.A1(_041_),
    .A2(_081_),
    .B1(_082_),
    .Y(_083_));
 sky130_fd_sc_hd__mux2i_1 _169_ (.A0(_004_),
    .A1(resp_msg[14]),
    .S(_032_),
    .Y(_084_));
 sky130_fd_sc_hd__nand2_1 _170_ (.A(req_msg[30]),
    .B(_041_),
    .Y(_085_));
 sky130_fd_sc_hd__o21ai_0 _171_ (.A1(_041_),
    .A2(_084_),
    .B1(_085_),
    .Y(_086_));
 sky130_fd_sc_hd__mux2_1 _172_ (.A0(_034_),
    .A1(req_msg[0]),
    .S(req_rdy),
    .X(_087_));
 sky130_fd_sc_hd__mux2_1 _173_ (.A0(_033_),
    .A1(req_msg[1]),
    .S(req_rdy),
    .X(_088_));
 sky130_fd_sc_hd__mux2_1 _174_ (.A0(_031_),
    .A1(req_msg[2]),
    .S(req_rdy),
    .X(_089_));
 sky130_fd_sc_hd__mux2_1 _175_ (.A0(_030_),
    .A1(req_msg[3]),
    .S(req_rdy),
    .X(_090_));
 sky130_fd_sc_hd__mux2_1 _176_ (.A0(_029_),
    .A1(req_msg[4]),
    .S(req_rdy),
    .X(_091_));
 sky130_fd_sc_hd__mux2_1 _177_ (.A0(_028_),
    .A1(req_msg[5]),
    .S(req_rdy),
    .X(_092_));
 sky130_fd_sc_hd__mux2_1 _178_ (.A0(_027_),
    .A1(req_msg[6]),
    .S(req_rdy),
    .X(_093_));
 sky130_fd_sc_hd__mux2_1 _179_ (.A0(_026_),
    .A1(req_msg[7]),
    .S(req_rdy),
    .X(_094_));
 sky130_fd_sc_hd__mux2_1 _180_ (.A0(_025_),
    .A1(req_msg[8]),
    .S(req_rdy),
    .X(_095_));
 sky130_fd_sc_hd__mux2_1 _181_ (.A0(_024_),
    .A1(req_msg[9]),
    .S(req_rdy),
    .X(_096_));
 sky130_fd_sc_hd__mux2_1 _182_ (.A0(_023_),
    .A1(req_msg[10]),
    .S(req_rdy),
    .X(_097_));
 sky130_fd_sc_hd__mux2_1 _183_ (.A0(_022_),
    .A1(req_msg[11]),
    .S(req_rdy),
    .X(_098_));
 sky130_fd_sc_hd__mux2_1 _184_ (.A0(_021_),
    .A1(req_msg[12]),
    .S(req_rdy),
    .X(_099_));
 sky130_fd_sc_hd__mux2_1 _185_ (.A0(_020_),
    .A1(req_msg[13]),
    .S(req_rdy),
    .X(_100_));
 sky130_fd_sc_hd__mux2_1 _186_ (.A0(_019_),
    .A1(req_msg[14]),
    .S(req_rdy),
    .X(_101_));
 sky130_fd_sc_hd__nor2_1 _187_ (.A(_036_),
    .B(_040_),
    .Y(resp_val));
 sky130_fd_sc_hd__a221o_1 _188_ (.A1(_112_),
    .A2(req_rdy),
    .B1(resp_val),
    .B2(resp_rdy),
    .C1(reset),
    .X(_102_));
 sky130_fd_sc_hd__nor2b_1 _189_ (.A(req_rdy),
    .B_N(resp_rdy),
    .Y(_103_));
 sky130_fd_sc_hd__nor4_1 _190_ (.A(_035_),
    .B(_010_),
    .C(_009_),
    .D(_008_),
    .Y(_104_));
 sky130_fd_sc_hd__nor4_1 _191_ (.A(_007_),
    .B(_006_),
    .C(_005_),
    .D(_004_),
    .Y(_105_));
 sky130_fd_sc_hd__nor4_1 _192_ (.A(_018_),
    .B(_017_),
    .C(_016_),
    .D(_011_),
    .Y(_106_));
 sky130_fd_sc_hd__nor4_1 _193_ (.A(_015_),
    .B(_014_),
    .C(_013_),
    .D(_012_),
    .Y(_107_));
 sky130_fd_sc_hd__and4_1 _194_ (.A(_104_),
    .B(_105_),
    .C(_106_),
    .D(_107_),
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
    .B1(_110_),
    .B2(_037_),
    .Y(_111_));
 sky130_fd_sc_hd__clkinv_1 _198_ (.A(req_val),
    .Y(_112_));
 sky130_fd_sc_hd__nor2b_1 _199_ (.A(reset),
    .B_N(_111_),
    .Y(_113_));
 sky130_fd_sc_hd__a22oi_1 _200_ (.A1(req_val),
    .A2(req_rdy),
    .B1(_002_),
    .B2(_109_),
    .Y(_114_));
 sky130_fd_sc_hd__nor2_1 _201_ (.A(reset),
    .B(_114_),
    .Y(_115_));
 sky130_fd_sc_hd__mux2i_1 _202_ (.A0(_035_),
    .A1(resp_msg[15]),
    .S(_032_),
    .Y(_116_));
 sky130_fd_sc_hd__nand2_1 _203_ (.A(req_msg[31]),
    .B(_041_),
    .Y(_117_));
 sky130_fd_sc_hd__o21ai_0 _204_ (.A1(_041_),
    .A2(_116_),
    .B1(_117_),
    .Y(_118_));
 sky130_fd_sc_hd__dfxtp_1 \ctrl.state.out[0]$_DFF_P_  (.D(_102_),
    .Q(req_rdy),
    .CLK(clk));
 sky130_fd_sc_hd__dfxtp_1 \ctrl.state.out[1]$_DFF_P_  (.D(_113_),
    .Q(_003_),
    .CLK(clk));
 sky130_fd_sc_hd__dfxtp_1 \ctrl.state.out[2]$_DFF_P_  (.D(_115_),
    .Q(_002_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[0]$_DFFE_PP_  (.D(_044_),
    .DE(_040_),
    .Q(_034_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[10]$_DFFE_PP_  (.D(_074_),
    .DE(_040_),
    .Q(_023_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[11]$_DFFE_PP_  (.D(_077_),
    .DE(_040_),
    .Q(_022_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[12]$_DFFE_PP_  (.D(_080_),
    .DE(_040_),
    .Q(_021_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[13]$_DFFE_PP_  (.D(_083_),
    .DE(_040_),
    .Q(_020_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[14]$_DFFE_PP_  (.D(_086_),
    .DE(_040_),
    .Q(_019_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[15]$_DFFE_PP_  (.D(_118_),
    .DE(_040_),
    .Q(_001_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[1]$_DFFE_PP_  (.D(_047_),
    .DE(_040_),
    .Q(_033_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[2]$_DFFE_PP_  (.D(_050_),
    .DE(_040_),
    .Q(_031_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[3]$_DFFE_PP_  (.D(_053_),
    .DE(_040_),
    .Q(_030_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[4]$_DFFE_PP_  (.D(_056_),
    .DE(_040_),
    .Q(_029_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[5]$_DFFE_PP_  (.D(_059_),
    .DE(_040_),
    .Q(_028_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[6]$_DFFE_PP_  (.D(_062_),
    .DE(_040_),
    .Q(_027_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[7]$_DFFE_PP_  (.D(_065_),
    .DE(_040_),
    .Q(_026_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[8]$_DFFE_PP_  (.D(_068_),
    .DE(_040_),
    .Q(_025_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.a_reg.out[9]$_DFFE_PP_  (.D(_071_),
    .DE(_040_),
    .Q(_024_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[0]$_DFFE_PP_  (.D(_087_),
    .DE(_038_),
    .Q(_018_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[10]$_DFFE_PP_  (.D(_097_),
    .DE(_038_),
    .Q(_008_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[11]$_DFFE_PP_  (.D(_098_),
    .DE(_038_),
    .Q(_007_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[12]$_DFFE_PP_  (.D(_099_),
    .DE(_038_),
    .Q(_006_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[13]$_DFFE_PP_  (.D(_100_),
    .DE(_038_),
    .Q(_005_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[14]$_DFFE_PP_  (.D(_101_),
    .DE(_038_),
    .Q(_004_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[15]$_DFFE_PP_  (.D(_039_),
    .DE(_038_),
    .Q(_035_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[1]$_DFFE_PP_  (.D(_088_),
    .DE(_038_),
    .Q(_017_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[2]$_DFFE_PP_  (.D(_089_),
    .DE(_038_),
    .Q(_016_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[3]$_DFFE_PP_  (.D(_090_),
    .DE(_038_),
    .Q(_015_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[4]$_DFFE_PP_  (.D(_091_),
    .DE(_038_),
    .Q(_014_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[5]$_DFFE_PP_  (.D(_092_),
    .DE(_038_),
    .Q(_013_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[6]$_DFFE_PP_  (.D(_093_),
    .DE(_038_),
    .Q(_012_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[7]$_DFFE_PP_  (.D(_094_),
    .DE(_038_),
    .Q(_011_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[8]$_DFFE_PP_  (.D(_095_),
    .DE(_038_),
    .Q(_010_),
    .CLK(clk));
 sky130_fd_sc_hd__edfxtp_1 \dpath.b_reg.out[9]$_DFFE_PP_  (.D(_096_),
    .DE(_038_),
    .Q(_009_),
    .CLK(clk));
endmodule
module \ALU_16_0_16_0_16_unused_CO[14:0]_X_HAN_CARLSON  (A,
    B,
    BI,
    CI,
    Y,
    \CO[15] );
 input [15:0] A;
 input [15:0] B;
 input BI;
 input CI;
 output [15:0] Y;
 output \CO[15] ;

 wire _000_;
 wire _001_;
 wire _002_;
 wire _003_;
 wire _004_;
 wire _005_;
 wire _006_;
 wire _007_;
 wire _008_;
 wire _009_;
 wire _010_;
 wire _011_;
 wire _012_;
 wire _013_;
 wire _014_;
 wire _015_;
 wire _016_;
 wire _017_;
 wire _018_;
 wire _019_;
 wire _020_;
 wire _021_;
 wire _022_;
 wire _023_;
 wire _024_;
 wire _025_;
 wire _026_;
 wire _027_;
 wire _028_;
 wire _029_;
 wire _030_;
 wire _031_;
 wire _032_;
 wire _033_;
 wire _034_;
 wire _035_;
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

 sky130_fd_sc_hd__xnor2_1 _085_ (.A(CI),
    .B(_084_),
    .Y(Y[0]));
 sky130_fd_sc_hd__maj3_1 _086_ (.A(CI),
    .B(A[0]),
    .C(_079_),
    .X(_000_));
 sky130_fd_sc_hd__xor2_1 _087_ (.A(BI),
    .B(B[1]),
    .X(_001_));
 sky130_fd_sc_hd__xnor2_1 _088_ (.A(A[1]),
    .B(_001_),
    .Y(_002_));
 sky130_fd_sc_hd__xnor2_1 _089_ (.A(_000_),
    .B(_002_),
    .Y(Y[1]));
 sky130_fd_sc_hd__maj3_1 _090_ (.A(A[1]),
    .B(_000_),
    .C(_001_),
    .X(_003_));
 sky130_fd_sc_hd__xor2_1 _091_ (.A(BI),
    .B(B[2]),
    .X(_004_));
 sky130_fd_sc_hd__nand2_1 _092_ (.A(A[2]),
    .B(_004_),
    .Y(_005_));
 sky130_fd_sc_hd__xnor2_1 _093_ (.A(A[2]),
    .B(_004_),
    .Y(_006_));
 sky130_fd_sc_hd__xnor2_1 _094_ (.A(_003_),
    .B(_006_),
    .Y(Y[2]));
 sky130_fd_sc_hd__maj3_1 _095_ (.A(A[2]),
    .B(_003_),
    .C(_004_),
    .X(_007_));
 sky130_fd_sc_hd__xor2_1 _096_ (.A(BI),
    .B(B[3]),
    .X(_008_));
 sky130_fd_sc_hd__nand2_1 _097_ (.A(A[3]),
    .B(_008_),
    .Y(_009_));
 sky130_fd_sc_hd__xnor2_1 _098_ (.A(A[3]),
    .B(_008_),
    .Y(_010_));
 sky130_fd_sc_hd__xnor2_1 _099_ (.A(_007_),
    .B(_010_),
    .Y(Y[3]));
 sky130_fd_sc_hd__nor2_1 _100_ (.A(_006_),
    .B(_010_),
    .Y(_011_));
 sky130_fd_sc_hd__o21ai_0 _101_ (.A1(_005_),
    .A2(_010_),
    .B1(_009_),
    .Y(_012_));
 sky130_fd_sc_hd__a21oi_1 _102_ (.A1(_003_),
    .A2(_011_),
    .B1(_012_),
    .Y(_013_));
 sky130_fd_sc_hd__xor2_1 _103_ (.A(BI),
    .B(B[4]),
    .X(_014_));
 sky130_fd_sc_hd__nand2_1 _104_ (.A(A[4]),
    .B(_014_),
    .Y(_015_));
 sky130_fd_sc_hd__xnor2_1 _105_ (.A(A[4]),
    .B(_014_),
    .Y(_016_));
 sky130_fd_sc_hd__xor2_1 _106_ (.A(_013_),
    .B(_016_),
    .X(Y[4]));
 sky130_fd_sc_hd__o21ai_0 _107_ (.A1(_013_),
    .A2(_016_),
    .B1(_015_),
    .Y(_017_));
 sky130_fd_sc_hd__xor2_1 _108_ (.A(BI),
    .B(B[5]),
    .X(_018_));
 sky130_fd_sc_hd__nand2_1 _109_ (.A(A[5]),
    .B(_018_),
    .Y(_019_));
 sky130_fd_sc_hd__xnor2_1 _110_ (.A(A[5]),
    .B(_018_),
    .Y(_020_));
 sky130_fd_sc_hd__xnor2_1 _111_ (.A(_017_),
    .B(_020_),
    .Y(Y[5]));
 sky130_fd_sc_hd__nor2_1 _112_ (.A(_016_),
    .B(_020_),
    .Y(_021_));
 sky130_fd_sc_hd__nor4_1 _113_ (.A(_006_),
    .B(_010_),
    .C(_016_),
    .D(_020_),
    .Y(_022_));
 sky130_fd_sc_hd__o21ai_0 _114_ (.A1(_015_),
    .A2(_020_),
    .B1(_019_),
    .Y(_023_));
 sky130_fd_sc_hd__a221oi_1 _115_ (.A1(_012_),
    .A2(_021_),
    .B1(_022_),
    .B2(_003_),
    .C1(_023_),
    .Y(_024_));
 sky130_fd_sc_hd__xor2_1 _116_ (.A(BI),
    .B(B[6]),
    .X(_025_));
 sky130_fd_sc_hd__nand2_1 _117_ (.A(A[6]),
    .B(_025_),
    .Y(_026_));
 sky130_fd_sc_hd__xnor2_1 _118_ (.A(A[6]),
    .B(_025_),
    .Y(_027_));
 sky130_fd_sc_hd__xor2_1 _119_ (.A(_024_),
    .B(_027_),
    .X(Y[6]));
 sky130_fd_sc_hd__o21ai_0 _120_ (.A1(_024_),
    .A2(_027_),
    .B1(_026_),
    .Y(_028_));
 sky130_fd_sc_hd__xor2_1 _121_ (.A(BI),
    .B(B[7]),
    .X(_029_));
 sky130_fd_sc_hd__nand2_1 _122_ (.A(A[7]),
    .B(_029_),
    .Y(_030_));
 sky130_fd_sc_hd__xnor2_1 _123_ (.A(A[7]),
    .B(_029_),
    .Y(_031_));
 sky130_fd_sc_hd__xnor2_1 _124_ (.A(_028_),
    .B(_031_),
    .Y(Y[7]));
 sky130_fd_sc_hd__nor2_1 _125_ (.A(_027_),
    .B(_031_),
    .Y(_032_));
 sky130_fd_sc_hd__o21ai_0 _126_ (.A1(_026_),
    .A2(_031_),
    .B1(_030_),
    .Y(_033_));
 sky130_fd_sc_hd__a21oi_1 _127_ (.A1(_023_),
    .A2(_032_),
    .B1(_033_),
    .Y(_034_));
 sky130_fd_sc_hd__nand2_1 _128_ (.A(_021_),
    .B(_032_),
    .Y(_035_));
 sky130_fd_sc_hd__o21ai_0 _129_ (.A1(_013_),
    .A2(_035_),
    .B1(_034_),
    .Y(_036_));
 sky130_fd_sc_hd__xor2_1 _130_ (.A(BI),
    .B(B[8]),
    .X(_037_));
 sky130_fd_sc_hd__nand2_1 _131_ (.A(A[8]),
    .B(_037_),
    .Y(_038_));
 sky130_fd_sc_hd__xnor2_1 _132_ (.A(A[8]),
    .B(_037_),
    .Y(_039_));
 sky130_fd_sc_hd__xnor2_1 _133_ (.A(_036_),
    .B(_039_),
    .Y(Y[8]));
 sky130_fd_sc_hd__maj3_1 _134_ (.A(A[8]),
    .B(_036_),
    .C(_037_),
    .X(_040_));
 sky130_fd_sc_hd__xor2_1 _135_ (.A(BI),
    .B(B[9]),
    .X(_041_));
 sky130_fd_sc_hd__nand2_1 _136_ (.A(A[9]),
    .B(_041_),
    .Y(_042_));
 sky130_fd_sc_hd__xnor2_1 _137_ (.A(A[9]),
    .B(_041_),
    .Y(_043_));
 sky130_fd_sc_hd__xnor2_1 _138_ (.A(_040_),
    .B(_043_),
    .Y(Y[9]));
 sky130_fd_sc_hd__nor2_1 _139_ (.A(_039_),
    .B(_043_),
    .Y(_044_));
 sky130_fd_sc_hd__o21ai_0 _140_ (.A1(_038_),
    .A2(_043_),
    .B1(_042_),
    .Y(_045_));
 sky130_fd_sc_hd__a21oi_1 _141_ (.A1(_033_),
    .A2(_044_),
    .B1(_045_),
    .Y(_046_));
 sky130_fd_sc_hd__nand2_1 _142_ (.A(_032_),
    .B(_044_),
    .Y(_047_));
 sky130_fd_sc_hd__clkinv_1 _143_ (.A(_049_),
    .Y(_048_));
 sky130_fd_sc_hd__o21ai_0 _144_ (.A1(_024_),
    .A2(_047_),
    .B1(_046_),
    .Y(_049_));
 sky130_fd_sc_hd__xor2_1 _145_ (.A(BI),
    .B(B[10]),
    .X(_050_));
 sky130_fd_sc_hd__nand2_1 _146_ (.A(A[10]),
    .B(_050_),
    .Y(_051_));
 sky130_fd_sc_hd__xnor2_1 _147_ (.A(A[10]),
    .B(_050_),
    .Y(_052_));
 sky130_fd_sc_hd__xnor2_1 _148_ (.A(_049_),
    .B(_052_),
    .Y(Y[10]));
 sky130_fd_sc_hd__o21ai_0 _149_ (.A1(_048_),
    .A2(_052_),
    .B1(_051_),
    .Y(_053_));
 sky130_fd_sc_hd__xor2_1 _150_ (.A(BI),
    .B(B[11]),
    .X(_054_));
 sky130_fd_sc_hd__nand2_1 _151_ (.A(A[11]),
    .B(_054_),
    .Y(_055_));
 sky130_fd_sc_hd__xnor2_1 _152_ (.A(A[11]),
    .B(_054_),
    .Y(_056_));
 sky130_fd_sc_hd__xnor2_1 _153_ (.A(_053_),
    .B(_056_),
    .Y(Y[11]));
 sky130_fd_sc_hd__nor2_1 _154_ (.A(_052_),
    .B(_056_),
    .Y(_057_));
 sky130_fd_sc_hd__o21ai_0 _155_ (.A1(_051_),
    .A2(_056_),
    .B1(_055_),
    .Y(_058_));
 sky130_fd_sc_hd__a21o_1 _156_ (.A1(_045_),
    .A2(_057_),
    .B1(_058_),
    .X(_059_));
 sky130_fd_sc_hd__a31oi_1 _157_ (.A1(_036_),
    .A2(_044_),
    .A3(_057_),
    .B1(_059_),
    .Y(_060_));
 sky130_fd_sc_hd__xor2_1 _158_ (.A(BI),
    .B(B[12]),
    .X(_061_));
 sky130_fd_sc_hd__nand2_1 _159_ (.A(A[12]),
    .B(_061_),
    .Y(_062_));
 sky130_fd_sc_hd__xnor2_1 _160_ (.A(A[12]),
    .B(_061_),
    .Y(_063_));
 sky130_fd_sc_hd__xor2_1 _161_ (.A(_060_),
    .B(_063_),
    .X(Y[12]));
 sky130_fd_sc_hd__o21ai_0 _162_ (.A1(_060_),
    .A2(_063_),
    .B1(_062_),
    .Y(_064_));
 sky130_fd_sc_hd__xor2_1 _163_ (.A(BI),
    .B(B[13]),
    .X(_065_));
 sky130_fd_sc_hd__nand2_1 _164_ (.A(A[13]),
    .B(_065_),
    .Y(_066_));
 sky130_fd_sc_hd__xnor2_1 _165_ (.A(A[13]),
    .B(_065_),
    .Y(_067_));
 sky130_fd_sc_hd__xnor2_1 _166_ (.A(_064_),
    .B(_067_),
    .Y(Y[13]));
 sky130_fd_sc_hd__nor2_1 _167_ (.A(_063_),
    .B(_067_),
    .Y(_068_));
 sky130_fd_sc_hd__nand2_1 _168_ (.A(_057_),
    .B(_068_),
    .Y(_069_));
 sky130_fd_sc_hd__nor3_1 _169_ (.A(_024_),
    .B(_047_),
    .C(_069_),
    .Y(_070_));
 sky130_fd_sc_hd__o21ai_0 _170_ (.A1(_062_),
    .A2(_067_),
    .B1(_066_),
    .Y(_071_));
 sky130_fd_sc_hd__a21oi_1 _171_ (.A1(_058_),
    .A2(_068_),
    .B1(_071_),
    .Y(_072_));
 sky130_fd_sc_hd__o21ai_0 _172_ (.A1(_046_),
    .A2(_069_),
    .B1(_072_),
    .Y(_073_));
 sky130_fd_sc_hd__nor2_1 _173_ (.A(_070_),
    .B(_073_),
    .Y(_074_));
 sky130_fd_sc_hd__xor2_1 _174_ (.A(BI),
    .B(B[14]),
    .X(_075_));
 sky130_fd_sc_hd__nand2_1 _175_ (.A(A[14]),
    .B(_075_),
    .Y(_076_));
 sky130_fd_sc_hd__xnor2_1 _176_ (.A(A[14]),
    .B(_075_),
    .Y(_077_));
 sky130_fd_sc_hd__xor2_1 _177_ (.A(_074_),
    .B(_077_),
    .X(Y[14]));
 sky130_fd_sc_hd__o21ai_0 _178_ (.A1(_074_),
    .A2(_077_),
    .B1(_076_),
    .Y(_078_));
 sky130_fd_sc_hd__xor2_1 _179_ (.A(BI),
    .B(B[0]),
    .X(_079_));
 sky130_fd_sc_hd__xor2_1 _180_ (.A(BI),
    .B(B[15]),
    .X(_080_));
 sky130_fd_sc_hd__xnor2_1 _181_ (.A(A[15]),
    .B(_080_),
    .Y(_081_));
 sky130_fd_sc_hd__xnor2_1 _182_ (.A(_078_),
    .B(_081_),
    .Y(Y[15]));
 sky130_fd_sc_hd__nor2_1 _183_ (.A(_076_),
    .B(_081_),
    .Y(_082_));
 sky130_fd_sc_hd__a21oi_1 _184_ (.A1(A[15]),
    .A2(_080_),
    .B1(_082_),
    .Y(_083_));
 sky130_fd_sc_hd__o31ai_1 _185_ (.A1(_074_),
    .A2(_077_),
    .A3(_081_),
    .B1(_083_),
    .Y(\CO[15] ));
 sky130_fd_sc_hd__xnor2_1 _186_ (.A(A[0]),
    .B(_079_),
    .Y(_084_));
endmodule
