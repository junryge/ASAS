package com.skhynix.smartatlas.navi;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import com.skhynix.smartatlas.data.raw.RawRouteInfo;

public class RouteResult {
	private final List<PathItem> path 					= new ArrayList<>();
	public double totalCost 							= 0;
	public Set<RawRouteInfo> routeSelectionSet 			= new HashSet<>();
	public List<String> routeSelectionLongEdgeIdList 	= new ArrayList<>();
	private long pathCnt 								= 0;
	private boolean pathRangeOverLogged 				= false;

	public RouteResult() {}

	public static class PathItem {
		public String longEdgeId 		= "";
		public double cost 				= 0;
		public boolean routeSelection 	= false;

		public PathItem() {}

		public PathItem(String longEdgeId, double cost) {
			this.longEdgeId	= longEdgeId;
			this.cost 		= cost;
		}
	}

	public List<PathItem> getPath() {
		return path;
	}

	public void addPathItem(PathItem pi) throws Exception {
		path.add(pi);

		pathCnt++;

		if (pathCnt > 1000 && !pathRangeOverLogged) {
			pathRangeOverLogged = true;

			throw new Exception("PathRangeOver1000");
		}
	}

	public void addPathItemList(List<PathItem> pis) throws Exception  {
		path.addAll(pis);

		pathCnt += pis.size();

		if (pathCnt > 1000 && !pathRangeOverLogged) {
			pathRangeOverLogged = true;

			throw new Exception("PathRangeOver1000");
		}
	}

}
