package model.input;

import model.Agent;
import model.Map;
import model.Player;
import model.XY;

public abstract class Input {

	public enum Option {
		TIME, LEGAL_MOVE, FOOD_ADJACENT, ENEMY_ADJACENT, ALLY_ADJACENT, PLANT_ADJACENT, PLANT_CURRENT, REPRODUCE_LEGAL, RANDOM, VALUE, HAS_FOOD, FOOD_VALUE, DIRT_VALUE, IN_BOUNDS, VALID_POSITION, OCCUPIED, POSITION_MATCH, GET_X, GET_Y, HAS_PLANT, HAS_ENEMY, HAS_ALLY, DIRECTION_TO, A_STAR, PLANT_RATE, TEAM_SIZE, CURRENT_TREE, NUMBER_TREES, MAP_WIDTH, MAP_HEIGHT, MAX_DIRT, MAX_FOOD, MAX_TEAM_SIZE, ENEMY_ADJACENT_POS, ALLY_ADJACENT_POS, CHECK_ATTACK_DOWN, CHECK_ATTACK_LEFT, CHECK_ATTACK_RIGHT, CHECK_ATTACK_UP, CHECK_CHANGE_TREE, CHECK_DEFEND, CHECK_DROP_DIRT, CHECK_DROP_FOOD, CHECK_EAT, CHECK_LIFT_DIRT, CHECK_LIFT_FOOD, CHECK_MOVE_DOWN, CHECK_MOVE_LEFT, CHECK_MOVE_RIGHT, CHECK_MOVE_UP, CHECK_REPRODUCE, CHECK_CLEAR_PRIMARY, CHECK_SET_PRIMARY, CHECK_CLEAR_SECONDARY, CHECK_SET_SECONDARY, CHECK_CONFUSED, SELF_X, SELF_Y, SELF_ACTION, SELF_PREVIOUS_X, SELF_PREVIOUS_Y, SELF_PREVIOUS_ACTION, SELF_SPEED, SELF_HEALTH, SELF_MAXHEALTH, SELF_POWER, SELF_EXP, SELF_DIRT, SELF_FOOD, SELF_AGE, ENEMY_X, ENEMY_Y, ENEMY_ACTION, ENEMY_SPEED, ENEMY_HEALTH, ENEMY_MAXHEALTH, ENEMY_POWER, ENEMY_EXP, ENEMY_DIRT, ENEMY_FOOD, ENEMY_AGE, ALLY_X, ALLY_Y, ALLY_ACTION, ALLY_SPEED, ALLY_HEALTH, ALLY_MAXHEALTH, ALLY_POWER, ALLY_EXP, ALLY_DIRT, ALLY_FOOD, ALLY_AGE
	};

	protected boolean inBounds(XY xy, Map map) {
		return inBounds(xy.getX(), xy.getY(), map);
	}

	protected boolean inBounds(int x, int y, Map map) {
		return (xInBounds(x, map) && yInBounds(y, map));
	}

	protected boolean xInBounds(int x, Map map) {
		return (x >= 0 && x < map.getWidth());
	}

	protected boolean yInBounds(int y, Map map) {
		return (y >= 0 && y < map.getHeight());
	}

	protected boolean occupied(int x, int y, Map map) {
		if (xInBounds(x, map) && yInBounds(y, map)) {
			return map.getTile(x, y).isOccupied();
		} else {
			return true;
		}
	}

	protected Agent checkAgent(int x, int y, Map map) {
		if (xInBounds(x, map) && yInBounds(y, map)) {
			if (map.getTile(x, y).isOccupied()) {
				return map.getTile(x, y).getAgent();
			} else {
				return null;
			}
		} else {
			return null;
		}
	}

	protected boolean hasEnemy(Player player, int x, int y, Map map) {
		return !player.equals(checkAgent(x, y, map).getPlayer());
	}

	protected boolean hasAlly(Player player, int x, int y, Map map) {
		return player.equals(checkAgent(x, y, map).getPlayer());
	}

	protected boolean hasPlant(int x, int y, Map map) {
		return map.getTile(x, y).getPlant() != null;
	}

	protected int checkFood(int x, int y, Map map) {
		if (xInBounds(x, map) && yInBounds(y, map)) {
			if (map.getTile(x, y).isOccupied()) {
				return map.getTile(x, y).getFood();
			} else {
				return 0;
			}
		} else {
			return 0;
		}
	}

	protected int checkDirt(int x, int y, Map map) {
		if (xInBounds(x, map) && yInBounds(y, map)) {
			if (map.getTile(x, y).isOccupied()) {
				return map.getTile(x, y).getDirt();
			} else {
				return 0;
			}
		} else {
			return 0;
		}
	}

	protected boolean hasFood(int x, int y, Map map) {
		return checkFood(x, y, map) > 0;
	}
}
