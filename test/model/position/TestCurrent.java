package model.position;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;

import org.junit.After;
import org.junit.Test;

import junit.framework.TestCase;
import main.Game;
import model.Agent;
import model.Map;
import model.XY;
import model.input.DecisionPosition;
import model.input.position.DirectionTo;
import model.output.Action.Activity;
import readers.ActionReaderImpl;
import readers.CriteriaReaderImpl;
import readers.GameReader;
import readers.GameReaderImpl;
import readers.InputReaderImpl;
import readers.MapReaderImpl;
import readers.ModeReaderImpl;
import readers.PlantReaderImpl;
import readers.PlayerReaderImpl;
import readers.PositionReaderImpl;
import readers.TreeReaderImpl;

public class TestCurrent extends TestCase {

	private GameReader gameReader;
	private final ByteArrayOutputStream outContent = new ByteArrayOutputStream();

	@Override
	protected void setUp() {
		gameReader = new GameReaderImpl(new MapReaderImpl(new PlantReaderImpl(),
				new PlayerReaderImpl(new TreeReaderImpl(new ActionReaderImpl(new PositionReaderImpl()), new InputReaderImpl(new PositionReaderImpl()))),
				new CriteriaReaderImpl(new ActionReaderImpl(new PositionReaderImpl())), new ModeReaderImpl()));
		System.setOut(new PrintStream(outContent));
	}
	
	@After
	public void cleanUpStreams() {
	    System.setOut(null);
	}

	@Test
	public void testCurrent_Success() {
		String file = "resources\\test\\positionMaps\\test_current_success.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);

		DecisionPosition decision = (DecisionPosition)agent.getTree().getRoot().getInputs().get(0);
		DirectionTo directionTo = (DirectionTo)decision;
		XY position = directionTo.getPosition().getPosition(agent, map);
		
		assertTrue(position.getX() == agent.getCurrentPos().getX());
		assertTrue(position.getY() == agent.getCurrentPos().getY());
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.DEFEND);
		assertTrue(map.getAllAgents().size() == 1);
	}
	
	@Test
	public void test_ToString() {
		Current position = new Current();
		String output = "CURRENT";
		assertTrue(position.toString().equals(output));
	}
}
