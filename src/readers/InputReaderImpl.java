package readers;

import java.util.List;

import model.input.GetPosition;
import model.input.Input;
import model.input.Input.Option;
import model.input.bool.AllyAction;
import model.input.bool.AllyAdjacent;
import model.input.bool.CurrentTree;
import model.input.bool.EnemyAction;
import model.input.bool.EnemyAdjacent;
import model.input.bool.FoodAdjacent;
import model.input.bool.HasAlly;
import model.input.bool.HasEnemy;
import model.input.bool.HasFood;
import model.input.bool.HasPlant;
import model.input.bool.InBounds;
import model.input.bool.LegalMove;
import model.input.bool.Occupied;
import model.input.bool.PlantAdjacent;
import model.input.bool.PlantCurrent;
import model.input.bool.PositionMatch;
import model.input.bool.PreviousAction;
import model.input.bool.ReproduceLegal;
import model.input.bool.ValidPosition;
import model.input.numeric.DirtValue;
import model.input.numeric.FoodValue;
import model.input.numeric.GetX;
import model.input.numeric.GetY;
import model.input.numeric.MapHeight;
import model.input.numeric.MapWidth;
import model.input.numeric.MaxDirt;
import model.input.numeric.MaxFood;
import model.input.numeric.MaxTeamSize;
import model.input.numeric.NumberTrees;
import model.input.numeric.PlantRate;
import model.input.numeric.RandomValue;
import model.input.numeric.TeamSize;
import model.input.numeric.Time;
import model.input.numeric.Value;
import model.input.position.AStar;
import model.input.position.AllyAdjacentPos;
import model.input.position.DirectionTo;
import model.input.position.EnemyAdjacentPos;

public class InputReaderImpl implements InputReader {

	private PositionReader positionReader;
	
	public InputReaderImpl(PositionReader positionReader) {
		setPositionReader(positionReader);
	}
	
	public PositionReader getPositionReader() {
		return positionReader;
	}

	public void setPositionReader(PositionReader positionReader) {
		this.positionReader = positionReader;
	}

	@Override
	public Input readInput(List<String> values) {
		Option option = Option.valueOf(values.get(0));
		String action = null;
		switch (option) {
		case TIME:
			values.remove(0);
			return new Time();
		case FOOD_ADJACENT:
			values.remove(0);
			return new FoodAdjacent();
		case ENEMY_ADJACENT:
			values.remove(0);
			return new EnemyAdjacent();
		case ALLY_ADJACENT:
			values.remove(0);
			return new AllyAdjacent();
		case PLANT_ADJACENT:
			values.remove(0);
			return new PlantAdjacent();
		case PLANT_CURRENT:
			values.remove(0);
			return new PlantCurrent();
		case REPRODUCE_LEGAL:
			values.remove(0);
			return new ReproduceLegal();
		case LEGAL_MOVE:
			values.remove(0);
			return new LegalMove();
		case RANDOM:
			values.remove(0);
			return new RandomValue();
		case VALUE:
			Value value = new Value(Integer.valueOf(values.get(1)));
			values.remove(0);
			values.remove(0);
			return value;
		case HAS_FOOD:
			values.remove(0);
			return new HasFood(getPositionReader().readPosition(values));
		case FOOD_VALUE:
			values.remove(0);
			return new FoodValue(getPositionReader().readPosition(values));
		case DIRT_VALUE:
			values.remove(0);
			return new DirtValue(getPositionReader().readPosition(values));
		case IN_BOUNDS:
			values.remove(0);
			return new InBounds(getPositionReader().readPosition(values));
		case OCCUPIED:
			values.remove(0);
			return new Occupied(getPositionReader().readPosition(values));
		case VALID_POSITION:
			values.remove(0);
			return new ValidPosition(getPositionReader().readPosition(values));
		case GET_X:
			values.remove(0);
			return new GetX(getPositionReader().readPosition(values));
		case GET_Y:
			values.remove(0);
			return new GetY(getPositionReader().readPosition(values));
		case POSITION_MATCH:
			values.remove(0);
			GetPosition position1 = getPositionReader().readPosition(values);
			GetPosition position2 = getPositionReader().readPosition(values);
			return new PositionMatch(position1, position2);
		case HAS_PLANT:
			values.remove(0);
			return new HasPlant(getPositionReader().readPosition(values));
		case HAS_ENEMY:
			values.remove(0);
			return new HasEnemy(getPositionReader().readPosition(values));
		case HAS_ALLY:
			values.remove(0);
			return new HasAlly(getPositionReader().readPosition(values));
		case DIRECTION_TO:
			values.remove(0);
			return new DirectionTo(getPositionReader().readPosition(values));
		case A_STAR:
			values.remove(0);
			return new AStar(getPositionReader().readPosition(values));
		case PLANT_RATE:
			values.remove(0);
			return new PlantRate(getPositionReader().readPosition(values));
		case ALLY_ACTION:
			action = values.get(1);
			values.remove(0);
			values.remove(0);
			AllyAction allyAction = new AllyAction(getPositionReader().readPosition(values), action);
			return allyAction;
		case ENEMY_ACTION:
			action = values.get(1);
			values.remove(0);
			values.remove(0);
			EnemyAction enemyAction = new EnemyAction(getPositionReader().readPosition(values), action);
			return enemyAction;
		case TEAM_SIZE:
			values.remove(0);
			return new TeamSize();
		case CURRENT_TREE:
			CurrentTree currentTree = new CurrentTree(values.get(1));
			values.remove(0);
			values.remove(0);
			return currentTree;
		case NUMBER_TREES:
			NumberTrees numberTrees = new NumberTrees(values.get(1));
			values.remove(0);
			values.remove(0);
			return numberTrees;
		case SELF_PREVIOUS_ACTION:
			PreviousAction previousAction = new PreviousAction(values.get(1));
			values.remove(0);
			values.remove(0);
			return previousAction;
		case MAP_WIDTH:
			values.remove(0);
			return new MapWidth();
		case MAP_HEIGHT:
			values.remove(0);
			return new MapHeight();
		case MAX_DIRT:
			values.remove(0);
			return new MaxDirt();
		case MAX_FOOD:
			values.remove(0);
			return new MaxFood();
		case MAX_TEAM_SIZE:
			values.remove(0);
			return new MaxTeamSize();
		case ENEMY_ADJACENT_POS:
			values.remove(0);
			return new EnemyAdjacentPos();
		case ALLY_ADJACENT_POS:
			values.remove(0);
			return new AllyAdjacentPos();
		default:
			System.out.println("InputReaderImpl: Invalid input name");
			return null;
		}
	}

}
