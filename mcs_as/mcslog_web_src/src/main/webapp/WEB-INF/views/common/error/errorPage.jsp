<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8"%>
<%@ include file="/WEB-INF/views/common-header.jspf"%>
<%@ include file="/WEB-INF/views/common-taglib.jspf"%>
<div id="lay_container">
	<div id="lay_contents">
        <div class="contents_wrap">
            <!-- Location Information -->
            <div class="loc_info_basic">
                <span class="location_box">
                    <a href="#" class="location"><span class="loc_info_ico loc_info_ico_home"></span>Home</a>
                </span>
                <span class="loc_info_ico loc_info_ico_arr_depth"></span>
                <span class="location_box">
                    <a href="#" class="location">error</a>
                </span>
            </div>
            <!-- //Location Information -->
            <!-- System Error -->
            <div class="system_error">
                <div class="error_contents">
                    <div class="error_ico_area">
                        <span class="system_error_ico system_error_ico_alert"></span>
                    </div>
                    <div class="error_txt">
                        <div class="error_title">이용에 불편을 드려 죄송합니다.</div>
                        <div class="error_description">시스템에 문제가 발생 하였습니다.<br/>담당자에게 문의하여 주시기 바랍니다.</div>
                        <div class="error_info">
                            <table class="error_table">
                                <tr>
                                    <th class="error_t_head">시스템 명</th>
                                    <td class="error_t_data">시스템 명을 적어주세요</td>
                                </tr>
                                <tr>
                                    <th class="error_t_head">담당자명</th>
                                    <td class="error_t_data">담당자명을 적어주세요</td>
                                </tr>
                                <tr>
                                    <th class="error_t_head">담당자 전화번호</th>
                                    <td class="error_t_data">02-1234-5678</td>
                                </tr>
                            </table>
                        </div>
                    </div>

                    <div class="error_btn_area btn_section">
                        <div class="center_section">
                            <a href="#" class="btn_txt btn_type_a btn_color_a">
                                <span class="txt"><spring:message code="common.page.prev" text="default text" /></span>
                            </a>
                            <a href="#" class="btn_txt btn_type_a btn_color_b">
                                <span class="txt"><spring:message code="site.common.button.home" text="default text" /></span>
                            </a>
                        </div>
                        <div class="clearboth"></div>
                    </div>
                </div>
            </div>
            <!-- //System Error -->
        </div>
    </div>
</div>