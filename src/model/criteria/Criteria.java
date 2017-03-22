package model.criteria;

import model.Map;

public interface Criteria {

	public enum Condition {
		ANNIHILATE, COLLECT_FOOD, LEVEL_UP, MAP_DIRT, SURVIVE_TURNS, TRAVEL_TO, PERFORM_ACTION, FIND_THING
	}; 
	public boolean isFinished(Map map) throws Exception;
}
